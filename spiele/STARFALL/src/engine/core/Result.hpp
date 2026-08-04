#pragma once

#include "Types.hpp"

#include <string>
#include <utility>

namespace sf {

enum class StatusCode : u32 {
    Ok = 0,
    NotFound,
    AlreadyExists,
    InvalidArgument,
    OutOfMemory,
    OutOfRange,
    IoFailure,
    DeviceFailure,
    ShaderFailure,
    NetworkFailure,
    ProtocolFailure,
    Timeout,
    PermissionDenied,
    Unsupported,
    Corrupt,
    Busy
};

struct Status {
    StatusCode code = StatusCode::Ok;
    std::string detail;

    bool ok() const { return code == StatusCode::Ok; }
    explicit operator bool() const { return ok(); }
};

inline Status statusOk() {
    return Status{StatusCode::Ok, std::string()};
}

inline Status statusError(StatusCode code, std::string detail) {
    return Status{code, std::move(detail)};
}

const char* statusName(StatusCode code);

template <typename T>
class Result {
public:
    Result(T value) : storedValue(std::move(value)), storedStatus(statusOk()) {}
    Result(Status status) : storedValue(), storedStatus(std::move(status)) {}

    bool ok() const { return storedStatus.ok(); }
    explicit operator bool() const { return ok(); }

    const Status& status() const { return storedStatus; }
    StatusCode code() const { return storedStatus.code; }
    const std::string& detail() const { return storedStatus.detail; }

    T& value() { return storedValue; }
    const T& value() const { return storedValue; }
    T valueOr(T fallback) const { return ok() ? storedValue : fallback; }

private:
    T storedValue;
    Status storedStatus;
};

template <typename T>
Result<T> resultOk(T value) {
    return Result<T>(std::move(value));
}

template <typename T>
Result<T> resultError(StatusCode code, std::string detail) {
    return Result<T>(statusError(code, std::move(detail)));
}

}
