#pragma once

#include "../core/Types.hpp"

#include <map>
#include <string>
#include <vector>

namespace sf {

class JsonValue {
public:
    enum class Kind : u32 { Null = 0, Boolean, Number, String, Array, Object };

    JsonValue() = default;
    explicit JsonValue(bool value) : kind(Kind::Boolean), booleanValue(value) {}
    explicit JsonValue(f64 value) : kind(Kind::Number), numberValue(value) {}
    explicit JsonValue(const std::string& value) : kind(Kind::String), stringValue(value) {}
    explicit JsonValue(const char* value) : kind(Kind::String), stringValue(value) {}

    static JsonValue makeArray();
    static JsonValue makeObject();
    static JsonValue parse(const std::string& text);

    Kind type() const { return kind; }
    bool isNull() const { return kind == Kind::Null; }
    bool isObject() const { return kind == Kind::Object; }
    bool isArray() const { return kind == Kind::Array; }

    bool boolean(bool fallback = false) const;
    f64 number(f64 fallback = 0.0) const;
    i64 integer(i64 fallback = 0) const;
    std::string text(const std::string& fallback = std::string()) const;

    const JsonValue& operator[](const std::string& key) const;
    const JsonValue& at(usize index) const;
    usize size() const;
    bool has(const std::string& key) const;

    void set(const std::string& key, const JsonValue& value);
    void set(const std::string& key, const std::string& value);
    void set(const std::string& key, f64 value);
    void set(const std::string& key, bool value);
    void push(const JsonValue& value);

    const std::map<std::string, JsonValue>& members() const { return objectValue; }
    const std::vector<JsonValue>& elements() const { return arrayValue; }

    std::string serialize() const;

private:
    static JsonValue parseValue(const std::string& text, usize& cursor);
    static void skipWhitespace(const std::string& text, usize& cursor);
    static std::string parseString(const std::string& text, usize& cursor);
    static std::string escape(const std::string& raw);

    Kind kind = Kind::Null;
    bool booleanValue = false;
    f64 numberValue = 0.0;
    std::string stringValue;
    std::vector<JsonValue> arrayValue;
    std::map<std::string, JsonValue> objectValue;
};

}
