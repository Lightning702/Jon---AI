#pragma once

#include "Mat3.hpp"
#include "Vec4.hpp"

namespace sf {

struct Mat4 {
    f32 m[16] = {1.0f, 0.0f, 0.0f, 0.0f,
                 0.0f, 1.0f, 0.0f, 0.0f,
                 0.0f, 0.0f, 1.0f, 0.0f,
                 0.0f, 0.0f, 0.0f, 1.0f};

    constexpr Mat4() = default;

    f32& at(u32 row, u32 column) { return m[column * 4 + row]; }
    f32 at(u32 row, u32 column) const { return m[column * 4 + row]; }

    static Mat4 identity() { return Mat4(); }

    static Mat4 translation(const Vec3& offset) {
        Mat4 result;
        result.m[12] = offset.x;
        result.m[13] = offset.y;
        result.m[14] = offset.z;
        return result;
    }

    static Mat4 scaling(const Vec3& factors) {
        Mat4 result;
        result.m[0] = factors.x;
        result.m[5] = factors.y;
        result.m[10] = factors.z;
        return result;
    }

    static Mat4 fromMat3(const Mat3& rotation) {
        Mat4 result;
        for (u32 column = 0; column < 3; ++column) {
            for (u32 row = 0; row < 3; ++row) {
                result.at(row, column) = rotation.at(row, column);
            }
        }
        return result;
    }

    static Mat4 lookAt(const Vec3& eye, const Vec3& target, const Vec3& upDirection) {
        const Vec3 forward = normalize(target - eye);
        const Vec3 right = normalize(cross(forward, upDirection));
        const Vec3 realUp = cross(right, forward);
        Mat4 result;
        result.m[0] = right.x;   result.m[4] = right.y;   result.m[8] = right.z;    result.m[12] = -dot(right, eye);
        result.m[1] = realUp.x;  result.m[5] = realUp.y;  result.m[9] = realUp.z;   result.m[13] = -dot(realUp, eye);
        result.m[2] = -forward.x; result.m[6] = -forward.y; result.m[10] = -forward.z; result.m[14] = dot(forward, eye);
        result.m[3] = 0.0f;      result.m[7] = 0.0f;      result.m[11] = 0.0f;      result.m[15] = 1.0f;
        return result;
    }

    static Mat4 perspective(f32 verticalFieldOfViewRadians, f32 aspectRatio, f32 nearPlane, f32 farPlane) {
        const f32 focal = 1.0f / std::tan(verticalFieldOfViewRadians * 0.5f);
        Mat4 result;
        for (u32 i = 0; i < 16; ++i) result.m[i] = 0.0f;
        result.m[0] = focal / aspectRatio;
        result.m[5] = focal;
        result.m[10] = (farPlane + nearPlane) / (nearPlane - farPlane);
        result.m[11] = -1.0f;
        result.m[14] = (2.0f * farPlane * nearPlane) / (nearPlane - farPlane);
        return result;
    }

    static Mat4 perspectiveInfiniteReverse(f32 verticalFieldOfViewRadians, f32 aspectRatio, f32 nearPlane) {
        const f32 focal = 1.0f / std::tan(verticalFieldOfViewRadians * 0.5f);
        Mat4 result;
        for (u32 i = 0; i < 16; ++i) result.m[i] = 0.0f;
        result.m[0] = focal / aspectRatio;
        result.m[5] = focal;
        result.m[10] = 0.0f;
        result.m[11] = -1.0f;
        result.m[14] = nearPlane;
        return result;
    }

    static Mat4 orthographic(f32 left, f32 right, f32 bottom, f32 top, f32 nearPlane, f32 farPlane) {
        Mat4 result;
        for (u32 i = 0; i < 16; ++i) result.m[i] = 0.0f;
        result.m[0] = 2.0f / (right - left);
        result.m[5] = 2.0f / (top - bottom);
        result.m[10] = -2.0f / (farPlane - nearPlane);
        result.m[12] = -(right + left) / (right - left);
        result.m[13] = -(top + bottom) / (top - bottom);
        result.m[14] = -(farPlane + nearPlane) / (farPlane - nearPlane);
        result.m[15] = 1.0f;
        return result;
    }

    Mat4 operator*(const Mat4& other) const {
        Mat4 result;
        for (u32 column = 0; column < 4; ++column) {
            for (u32 row = 0; row < 4; ++row) {
                f32 sum = 0.0f;
                for (u32 k = 0; k < 4; ++k) sum += at(row, k) * other.at(k, column);
                result.at(row, column) = sum;
            }
        }
        return result;
    }

    Vec4 operator*(const Vec4& v) const {
        return Vec4(m[0] * v.x + m[4] * v.y + m[8] * v.z + m[12] * v.w,
                    m[1] * v.x + m[5] * v.y + m[9] * v.z + m[13] * v.w,
                    m[2] * v.x + m[6] * v.y + m[10] * v.z + m[14] * v.w,
                    m[3] * v.x + m[7] * v.y + m[11] * v.z + m[15] * v.w);
    }

    Vec3 transformPoint(const Vec3& point) const {
        const Vec4 result = (*this) * Vec4(point, 1.0f);
        const f32 inverseW = result.w != 0.0f ? 1.0f / result.w : 1.0f;
        return Vec3(result.x * inverseW, result.y * inverseW, result.z * inverseW);
    }

    Vec3 transformDirection(const Vec3& direction) const {
        return ((*this) * Vec4(direction, 0.0f)).xyz();
    }

    Mat3 upperLeft3x3() const {
        Mat3 result;
        for (u32 column = 0; column < 3; ++column) {
            for (u32 row = 0; row < 3; ++row) {
                result.at(row, column) = at(row, column);
            }
        }
        return result;
    }

    Mat4 transposed() const {
        Mat4 result;
        for (u32 row = 0; row < 4; ++row) {
            for (u32 column = 0; column < 4; ++column) {
                result.at(row, column) = at(column, row);
            }
        }
        return result;
    }

    Mat4 inverted() const;
};

inline Mat4 Mat4::inverted() const {
    const f32* a = m;
    f32 inverse[16];

    inverse[0] = a[5] * a[10] * a[15] - a[5] * a[11] * a[14] - a[9] * a[6] * a[15] +
                 a[9] * a[7] * a[14] + a[13] * a[6] * a[11] - a[13] * a[7] * a[10];
    inverse[4] = -a[4] * a[10] * a[15] + a[4] * a[11] * a[14] + a[8] * a[6] * a[15] -
                 a[8] * a[7] * a[14] - a[12] * a[6] * a[11] + a[12] * a[7] * a[10];
    inverse[8] = a[4] * a[9] * a[15] - a[4] * a[11] * a[13] - a[8] * a[5] * a[15] +
                 a[8] * a[7] * a[13] + a[12] * a[5] * a[11] - a[12] * a[7] * a[9];
    inverse[12] = -a[4] * a[9] * a[14] + a[4] * a[10] * a[13] + a[8] * a[5] * a[14] -
                  a[8] * a[6] * a[13] - a[12] * a[5] * a[10] + a[12] * a[6] * a[9];
    inverse[1] = -a[1] * a[10] * a[15] + a[1] * a[11] * a[14] + a[9] * a[2] * a[15] -
                 a[9] * a[3] * a[14] - a[13] * a[2] * a[11] + a[13] * a[3] * a[10];
    inverse[5] = a[0] * a[10] * a[15] - a[0] * a[11] * a[14] - a[8] * a[2] * a[15] +
                 a[8] * a[3] * a[14] + a[12] * a[2] * a[11] - a[12] * a[3] * a[10];
    inverse[9] = -a[0] * a[9] * a[15] + a[0] * a[11] * a[13] + a[8] * a[1] * a[15] -
                 a[8] * a[3] * a[13] - a[12] * a[1] * a[11] + a[12] * a[3] * a[9];
    inverse[13] = a[0] * a[9] * a[14] - a[0] * a[10] * a[13] - a[8] * a[1] * a[14] +
                  a[8] * a[2] * a[13] + a[12] * a[1] * a[10] - a[12] * a[2] * a[9];
    inverse[2] = a[1] * a[6] * a[15] - a[1] * a[7] * a[14] - a[5] * a[2] * a[15] +
                 a[5] * a[3] * a[14] + a[13] * a[2] * a[7] - a[13] * a[3] * a[6];
    inverse[6] = -a[0] * a[6] * a[15] + a[0] * a[7] * a[14] + a[4] * a[2] * a[15] -
                 a[4] * a[3] * a[14] - a[12] * a[2] * a[7] + a[12] * a[3] * a[6];
    inverse[10] = a[0] * a[5] * a[15] - a[0] * a[7] * a[13] - a[4] * a[1] * a[15] +
                  a[4] * a[3] * a[13] + a[12] * a[1] * a[7] - a[12] * a[3] * a[5];
    inverse[14] = -a[0] * a[5] * a[14] + a[0] * a[6] * a[13] + a[4] * a[1] * a[14] -
                  a[4] * a[2] * a[13] - a[12] * a[1] * a[6] + a[12] * a[2] * a[5];
    inverse[3] = -a[1] * a[6] * a[11] + a[1] * a[7] * a[10] + a[5] * a[2] * a[11] -
                 a[5] * a[3] * a[10] - a[9] * a[2] * a[7] + a[9] * a[3] * a[6];
    inverse[7] = a[0] * a[6] * a[11] - a[0] * a[7] * a[10] - a[4] * a[2] * a[11] +
                 a[4] * a[3] * a[10] + a[8] * a[2] * a[7] - a[8] * a[3] * a[6];
    inverse[11] = -a[0] * a[5] * a[11] + a[0] * a[7] * a[9] + a[4] * a[1] * a[11] -
                  a[4] * a[3] * a[9] - a[8] * a[1] * a[7] + a[8] * a[3] * a[5];
    inverse[15] = a[0] * a[5] * a[10] - a[0] * a[6] * a[9] - a[4] * a[1] * a[10] +
                  a[4] * a[2] * a[9] + a[8] * a[1] * a[6] - a[8] * a[2] * a[5];

    f32 determinant = a[0] * inverse[0] + a[1] * inverse[4] + a[2] * inverse[8] + a[3] * inverse[12];
    Mat4 result;
    if (determinant == 0.0f) return result;
    determinant = 1.0f / determinant;
    for (u32 i = 0; i < 16; ++i) result.m[i] = inverse[i] * determinant;
    return result;
}

}
