#include "Json.hpp"

#include <cstdio>
#include <cstdlib>

namespace sf {
namespace {

const JsonValue kNullValue;

}

JsonValue JsonValue::makeArray() {
    JsonValue value;
    value.kind = Kind::Array;
    return value;
}

JsonValue JsonValue::makeObject() {
    JsonValue value;
    value.kind = Kind::Object;
    return value;
}

bool JsonValue::boolean(bool fallback) const {
    if (kind == Kind::Boolean) return booleanValue;
    if (kind == Kind::Number) return numberValue != 0.0;
    return fallback;
}

f64 JsonValue::number(f64 fallback) const {
    if (kind == Kind::Number) return numberValue;
    if (kind == Kind::Boolean) return booleanValue ? 1.0 : 0.0;
    if (kind == Kind::String) return std::strtod(stringValue.c_str(), nullptr);
    return fallback;
}

i64 JsonValue::integer(i64 fallback) const {
    if (kind == Kind::Number) return static_cast<i64>(numberValue);
    if (kind == Kind::String) return std::strtoll(stringValue.c_str(), nullptr, 10);
    return fallback;
}

std::string JsonValue::text(const std::string& fallback) const {
    if (kind == Kind::String) return stringValue;
    if (kind == Kind::Number) {
        char buffer[64];
        std::snprintf(buffer, sizeof(buffer), "%.10g", numberValue);
        return buffer;
    }
    if (kind == Kind::Boolean) return booleanValue ? "true" : "false";
    return fallback;
}

const JsonValue& JsonValue::operator[](const std::string& key) const {
    if (kind != Kind::Object) return kNullValue;
    auto found = objectValue.find(key);
    return found == objectValue.end() ? kNullValue : found->second;
}

const JsonValue& JsonValue::at(usize index) const {
    if (kind != Kind::Array || index >= arrayValue.size()) return kNullValue;
    return arrayValue[index];
}

usize JsonValue::size() const {
    if (kind == Kind::Array) return arrayValue.size();
    if (kind == Kind::Object) return objectValue.size();
    return 0;
}

bool JsonValue::has(const std::string& key) const {
    return kind == Kind::Object && objectValue.find(key) != objectValue.end();
}

void JsonValue::set(const std::string& key, const JsonValue& value) {
    kind = Kind::Object;
    objectValue[key] = value;
}

void JsonValue::set(const std::string& key, const std::string& value) {
    set(key, JsonValue(value));
}

void JsonValue::set(const std::string& key, f64 value) {
    set(key, JsonValue(value));
}

void JsonValue::set(const std::string& key, bool value) {
    set(key, JsonValue(value));
}

void JsonValue::push(const JsonValue& value) {
    kind = Kind::Array;
    arrayValue.push_back(value);
}

std::string JsonValue::escape(const std::string& raw) {
    std::string result;
    result.reserve(raw.size() + 8);
    for (char character : raw) {
        switch (character) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default:
                if (static_cast<u8>(character) < 0x20) {
                    char buffer[8];
                    std::snprintf(buffer, sizeof(buffer), "\\u%04x", static_cast<u32>(static_cast<u8>(character)));
                    result += buffer;
                } else {
                    result += character;
                }
                break;
        }
    }
    return result;
}

std::string JsonValue::serialize() const {
    switch (kind) {
        case Kind::Null: return "null";
        case Kind::Boolean: return booleanValue ? "true" : "false";
        case Kind::Number: {
            char buffer[64];
            std::snprintf(buffer, sizeof(buffer), "%.10g", numberValue);
            return buffer;
        }
        case Kind::String: return "\"" + escape(stringValue) + "\"";
        case Kind::Array: {
            std::string result = "[";
            for (usize index = 0; index < arrayValue.size(); ++index) {
                if (index > 0) result += ",";
                result += arrayValue[index].serialize();
            }
            return result + "]";
        }
        case Kind::Object: {
            std::string result = "{";
            bool first = true;
            for (const auto& entry : objectValue) {
                if (!first) result += ",";
                first = false;
                result += "\"" + escape(entry.first) + "\":" + entry.second.serialize();
            }
            return result + "}";
        }
    }
    return "null";
}

void JsonValue::skipWhitespace(const std::string& text, usize& cursor) {
    while (cursor < text.size()) {
        const char character = text[cursor];
        if (character == ' ' || character == '\t' || character == '\n' || character == '\r') ++cursor;
        else break;
    }
}

std::string JsonValue::parseString(const std::string& text, usize& cursor) {
    std::string result;
    if (cursor >= text.size() || text[cursor] != '"') return result;
    ++cursor;
    while (cursor < text.size()) {
        const char character = text[cursor++];
        if (character == '"') break;
        if (character != '\\') {
            result += character;
            continue;
        }
        if (cursor >= text.size()) break;
        const char escaped = text[cursor++];
        switch (escaped) {
            case 'n': result += '\n'; break;
            case 't': result += '\t'; break;
            case 'r': result += '\r'; break;
            case 'b': result += '\b'; break;
            case 'f': result += '\f'; break;
            case 'u': {
                if (cursor + 4 <= text.size()) {
                    const std::string hex = text.substr(cursor, 4);
                    cursor += 4;
                    const u32 codepoint = static_cast<u32>(std::strtoul(hex.c_str(), nullptr, 16));
                    if (codepoint < 0x80) {
                        result += static_cast<char>(codepoint);
                    } else if (codepoint < 0x800) {
                        result += static_cast<char>(0xC0 | (codepoint >> 6));
                        result += static_cast<char>(0x80 | (codepoint & 0x3F));
                    } else {
                        result += static_cast<char>(0xE0 | (codepoint >> 12));
                        result += static_cast<char>(0x80 | ((codepoint >> 6) & 0x3F));
                        result += static_cast<char>(0x80 | (codepoint & 0x3F));
                    }
                }
                break;
            }
            default: result += escaped; break;
        }
    }
    return result;
}

JsonValue JsonValue::parseValue(const std::string& text, usize& cursor) {
    skipWhitespace(text, cursor);
    if (cursor >= text.size()) return JsonValue();

    const char character = text[cursor];
    if (character == '{') {
        ++cursor;
        JsonValue object = makeObject();
        skipWhitespace(text, cursor);
        if (cursor < text.size() && text[cursor] == '}') {
            ++cursor;
            return object;
        }
        while (cursor < text.size()) {
            skipWhitespace(text, cursor);
            const std::string key = parseString(text, cursor);
            skipWhitespace(text, cursor);
            if (cursor < text.size() && text[cursor] == ':') ++cursor;
            object.objectValue[key] = parseValue(text, cursor);
            skipWhitespace(text, cursor);
            if (cursor < text.size() && text[cursor] == ',') {
                ++cursor;
                continue;
            }
            if (cursor < text.size() && text[cursor] == '}') ++cursor;
            break;
        }
        return object;
    }

    if (character == '[') {
        ++cursor;
        JsonValue array = makeArray();
        skipWhitespace(text, cursor);
        if (cursor < text.size() && text[cursor] == ']') {
            ++cursor;
            return array;
        }
        while (cursor < text.size()) {
            array.arrayValue.push_back(parseValue(text, cursor));
            skipWhitespace(text, cursor);
            if (cursor < text.size() && text[cursor] == ',') {
                ++cursor;
                continue;
            }
            if (cursor < text.size() && text[cursor] == ']') ++cursor;
            break;
        }
        return array;
    }

    if (character == '"') {
        return JsonValue(parseString(text, cursor));
    }

    if (text.compare(cursor, 4, "true") == 0) {
        cursor += 4;
        return JsonValue(true);
    }
    if (text.compare(cursor, 5, "false") == 0) {
        cursor += 5;
        return JsonValue(false);
    }
    if (text.compare(cursor, 4, "null") == 0) {
        cursor += 4;
        return JsonValue();
    }

    char* end = nullptr;
    const f64 parsed = std::strtod(text.c_str() + cursor, &end);
    if (end != nullptr && end != text.c_str() + cursor) {
        cursor = static_cast<usize>(end - text.c_str());
        return JsonValue(parsed);
    }
    ++cursor;
    return JsonValue();
}

JsonValue JsonValue::parse(const std::string& text) {
    usize cursor = 0;
    return parseValue(text, cursor);
}

}
