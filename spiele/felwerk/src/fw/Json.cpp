#include "Json.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace fw {
namespace js {

namespace {
const Value kNull;

struct Reader {
    const std::string& text;
    size_t pos = 0;
    bool failed = false;

    explicit Reader(const std::string& t) : text(t) {}

    void skip() {
        while (pos < text.size()) {
            char c = text[pos];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r') pos++;
            else break;
        }
    }
    bool eof() const { return pos >= text.size(); }
    char peek() const { return pos < text.size() ? text[pos] : '\0'; }
    bool eat(char c) {
        skip();
        if (peek() != c) return false;
        pos++;
        return true;
    }

    Value parseValue(int depth) {
        skip();
        if (depth > 64 || eof()) {
            failed = true;
            return Value();
        }
        char c = peek();
        if (c == '{') return parseObject(depth);
        if (c == '[') return parseArray(depth);
        if (c == '"') return Value::string(parseString());
        if (c == 't') {
            if (text.compare(pos, 4, "true") == 0) { pos += 4; return Value::boolean(true); }
            failed = true;
            return Value();
        }
        if (c == 'f') {
            if (text.compare(pos, 5, "false") == 0) { pos += 5; return Value::boolean(false); }
            failed = true;
            return Value();
        }
        if (c == 'n') {
            if (text.compare(pos, 4, "null") == 0) { pos += 4; return Value(); }
            failed = true;
            return Value();
        }
        return parseNumber();
    }

    Value parseObject(int depth) {
        Value out = Value::object();
        pos++;
        skip();
        if (eat('}')) return out;
        while (!eof()) {
            skip();
            if (peek() != '"') { failed = true; return out; }
            std::string key = parseString();
            if (!eat(':')) { failed = true; return out; }
            out.set(key, parseValue(depth + 1));
            if (failed) return out;
            skip();
            if (eat(',')) continue;
            if (eat('}')) return out;
            failed = true;
            return out;
        }
        failed = true;
        return out;
    }

    Value parseArray(int depth) {
        Value out = Value::array();
        pos++;
        skip();
        if (eat(']')) return out;
        while (!eof()) {
            out.push(parseValue(depth + 1));
            if (failed) return out;
            skip();
            if (eat(',')) continue;
            if (eat(']')) return out;
            failed = true;
            return out;
        }
        failed = true;
        return out;
    }

    std::string parseString() {
        std::string out;
        pos++;
        while (pos < text.size()) {
            char c = text[pos++];
            if (c == '"') return out;
            if (c != '\\') {
                out.push_back(c);
                continue;
            }
            if (pos >= text.size()) break;
            char esc = text[pos++];
            switch (esc) {
            case 'n': out.push_back('\n'); break;
            case 't': out.push_back('\t'); break;
            case 'r': out.push_back('\r'); break;
            case 'b': out.push_back('\b'); break;
            case 'f': out.push_back('\f'); break;
            case '/': out.push_back('/'); break;
            case '"': out.push_back('"'); break;
            case '\\': out.push_back('\\'); break;
            case 'u': {
                if (pos + 4 > text.size()) { failed = true; return out; }
                unsigned code = 0;
                for (int i = 0; i < 4; i++) {
                    char h = text[pos + (size_t)i];
                    code <<= 4;
                    if (h >= '0' && h <= '9') code |= (unsigned)(h - '0');
                    else if (h >= 'a' && h <= 'f') code |= (unsigned)(h - 'a' + 10);
                    else if (h >= 'A' && h <= 'F') code |= (unsigned)(h - 'A' + 10);
                    else { failed = true; return out; }
                }
                pos += 4;
                if (code < 0x80) {
                    out.push_back((char)code);
                } else if (code < 0x800) {
                    out.push_back((char)(0xC0 | (code >> 6)));
                    out.push_back((char)(0x80 | (code & 0x3F)));
                } else {
                    out.push_back((char)(0xE0 | (code >> 12)));
                    out.push_back((char)(0x80 | ((code >> 6) & 0x3F)));
                    out.push_back((char)(0x80 | (code & 0x3F)));
                }
                break;
            }
            default:
                out.push_back(esc);
                break;
            }
        }
        failed = true;
        return out;
    }

    Value parseNumber() {
        size_t start = pos;
        if (peek() == '-' || peek() == '+') pos++;
        bool digits = false;
        while (pos < text.size()) {
            char c = text[pos];
            if ((c >= '0' && c <= '9')) { digits = true; pos++; }
            else if (c == '.' || c == 'e' || c == 'E' || c == '-' || c == '+') pos++;
            else break;
        }
        if (!digits) {
            failed = true;
            return Value();
        }
        return Value::number(std::strtod(text.substr(start, pos - start).c_str(), nullptr));
    }
};
}

Value Value::object() {
    Value v;
    v.kind = JS_OBJECT;
    return v;
}
Value Value::array() {
    Value v;
    v.kind = JS_ARRAY;
    return v;
}
Value Value::boolean(bool b) {
    Value v;
    v.kind = JS_BOOL;
    v.bool_ = b;
    return v;
}
Value Value::number(double n) {
    Value v;
    v.kind = JS_NUMBER;
    v.number_ = n;
    return v;
}
Value Value::string(const std::string& s) {
    Value v;
    v.kind = JS_STRING;
    v.string_ = s;
    return v;
}

bool Value::asBool(bool fallback) const {
    if (kind == JS_BOOL) return bool_;
    if (kind == JS_NUMBER) return number_ != 0.0;
    return fallback;
}
double Value::asNumber(double fallback) const {
    if (kind == JS_NUMBER) return number_;
    if (kind == JS_BOOL) return bool_ ? 1.0 : 0.0;
    if (kind == JS_STRING) return std::strtod(string_.c_str(), nullptr);
    return fallback;
}
std::string Value::asString(const std::string& fallback) const {
    if (kind == JS_STRING) return string_;
    if (kind == JS_NUMBER) {
        char buf[40];
        std::snprintf(buf, sizeof(buf), "%g", number_);
        return std::string(buf);
    }
    if (kind == JS_BOOL) return bool_ ? "true" : "false";
    return fallback;
}

bool Value::has(const std::string& key) const {
    return kind == JS_OBJECT && object_.find(key) != object_.end();
}
const Value& Value::get(const std::string& key) const {
    if (kind != JS_OBJECT) return kNull;
    std::map<std::string, Value>::const_iterator it = object_.find(key);
    return it == object_.end() ? kNull : it->second;
}
Value& Value::operator[](const std::string& key) {
    if (kind != JS_OBJECT) {
        kind = JS_OBJECT;
        object_.clear();
    }
    return object_[key];
}
void Value::set(const std::string& key, const Value& v) {
    if (kind != JS_OBJECT) {
        kind = JS_OBJECT;
        object_.clear();
    }
    object_[key] = v;
}
const Value& Value::at(size_t index) const {
    if (kind != JS_ARRAY || index >= array_.size()) return kNull;
    return array_[index];
}
void Value::push(const Value& v) {
    if (kind != JS_ARRAY) {
        kind = JS_ARRAY;
        array_.clear();
    }
    array_.push_back(v);
}

std::string escape(const std::string& text) {
    std::string out;
    out.reserve(text.size() + 8);
    for (size_t i = 0; i < text.size(); i++) {
        unsigned char c = (unsigned char)text[i];
        switch (c) {
        case '"': out += "\\\""; break;
        case '\\': out += "\\\\"; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        default:
            if (c < 0x20) {
                char buf[8];
                std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                out += buf;
            } else {
                out.push_back((char)c);
            }
            break;
        }
    }
    return out;
}

void Value::writeTo(std::string& out) const {
    switch (kind) {
    case JS_NULL: out += "null"; break;
    case JS_BOOL: out += bool_ ? "true" : "false"; break;
    case JS_NUMBER: {
        if (!std::isfinite(number_)) {
            out += "0";
            break;
        }
        char buf[40];
        if (number_ == (double)(long long)number_ && std::fabs(number_) < 1e15) {
            std::snprintf(buf, sizeof(buf), "%lld", (long long)number_);
        } else {
            std::snprintf(buf, sizeof(buf), "%.4f", number_);
        }
        out += buf;
        break;
    }
    case JS_STRING:
        out.push_back('"');
        out += escape(string_);
        out.push_back('"');
        break;
    case JS_ARRAY: {
        out.push_back('[');
        for (size_t i = 0; i < array_.size(); i++) {
            if (i) out.push_back(',');
            array_[i].writeTo(out);
        }
        out.push_back(']');
        break;
    }
    default: {
        out.push_back('{');
        bool first = true;
        for (std::map<std::string, Value>::const_iterator it = object_.begin(); it != object_.end(); ++it) {
            if (!first) out.push_back(',');
            first = false;
            out.push_back('"');
            out += escape(it->first);
            out += "\":";
            it->second.writeTo(out);
        }
        out.push_back('}');
        break;
    }
    }
}

std::string Value::dump() const {
    std::string out;
    out.reserve(128);
    writeTo(out);
    return out;
}

Value parse(const std::string& text, bool* ok) {
    Reader reader(text);
    Value value = reader.parseValue(0);
    if (ok) *ok = !reader.failed;
    return value;
}

}
}
