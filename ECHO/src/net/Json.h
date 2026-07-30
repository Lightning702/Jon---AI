#pragma once

#include "../core/Common.h"
#include <map>
#include <string>
#include <vector>

namespace echo {
namespace js {

enum ValueType { JS_NULL = 0, JS_BOOL, JS_NUMBER, JS_STRING, JS_ARRAY, JS_OBJECT };

class Value {
public:
    Value() {}
    static Value object();
    static Value array();
    static Value boolean(bool v);
    static Value number(double v);
    static Value string(const std::string& v);

    int type() const { return kind; }
    bool isNull() const { return kind == JS_NULL; }
    bool isObject() const { return kind == JS_OBJECT; }
    bool isArray() const { return kind == JS_ARRAY; }
    bool isNumber() const { return kind == JS_NUMBER; }
    bool isString() const { return kind == JS_STRING; }
    bool isBool() const { return kind == JS_BOOL; }

    bool asBool(bool fallback = false) const;
    double asNumber(double fallback = 0.0) const;
    float asFloat(float fallback = 0.0f) const { return (float)asNumber((double)fallback); }
    int asInt(int fallback = 0) const { return (int)asNumber((double)fallback); }
    std::string asString(const std::string& fallback = std::string()) const;

    bool has(const std::string& key) const;
    const Value& get(const std::string& key) const;
    Value& operator[](const std::string& key);
    const std::map<std::string, Value>& members() const { return object_; }

    size_t size() const { return array_.size(); }
    const Value& at(size_t index) const;
    void push(const Value& v);
    std::vector<Value>& items() { return array_; }
    const std::vector<Value>& items() const { return array_; }

    void set(const std::string& key, const Value& v);
    void set(const std::string& key, const std::string& v) { set(key, string(v)); }
    void set(const std::string& key, const char* v) { set(key, string(std::string(v))); }
    void set(const std::string& key, double v) { set(key, number(v)); }
    void set(const std::string& key, float v) { set(key, number((double)v)); }
    void set(const std::string& key, int v) { set(key, number((double)v)); }
    void set(const std::string& key, bool v) { set(key, boolean(v)); }

    std::string dump() const;

private:
    void writeTo(std::string& out) const;

    int kind = JS_NULL;
    bool bool_ = false;
    double number_ = 0.0;
    std::string string_;
    std::vector<Value> array_;
    std::map<std::string, Value> object_;
};

Value parse(const std::string& text, bool* ok = nullptr);
std::string escape(const std::string& text);

}
}
