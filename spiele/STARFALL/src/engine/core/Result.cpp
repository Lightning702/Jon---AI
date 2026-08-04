#include "Result.hpp"

namespace sf {

const char* statusName(StatusCode code) {
    switch (code) {
        case StatusCode::Ok: return "ok";
        case StatusCode::NotFound: return "not_found";
        case StatusCode::AlreadyExists: return "already_exists";
        case StatusCode::InvalidArgument: return "invalid_argument";
        case StatusCode::OutOfMemory: return "out_of_memory";
        case StatusCode::OutOfRange: return "out_of_range";
        case StatusCode::IoFailure: return "io_failure";
        case StatusCode::DeviceFailure: return "device_failure";
        case StatusCode::ShaderFailure: return "shader_failure";
        case StatusCode::NetworkFailure: return "network_failure";
        case StatusCode::ProtocolFailure: return "protocol_failure";
        case StatusCode::Timeout: return "timeout";
        case StatusCode::PermissionDenied: return "permission_denied";
        case StatusCode::Unsupported: return "unsupported";
        case StatusCode::Corrupt: return "corrupt";
        case StatusCode::Busy: return "busy";
    }
    return "unknown";
}

}
