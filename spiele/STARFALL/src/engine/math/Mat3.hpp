#pragma once

#include "Vec3.hpp"

namespace sf {

struct Mat3 {
    f32 m[9] = {1.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 0.0f, 1.0f};

    constexpr Mat3() = default;

    f32& at(u32 row, u32 column) { return m[column * 3 + row]; }
    f32 at(u32 row, u32 column) const { return m[column * 3 + row]; }

    Vec3 column(u32 index) const { return Vec3(m[index * 3 + 0], m[index * 3 + 1], m[index * 3 + 2]); }

    static Mat3 identity() { return Mat3(); }

    static Mat3 fromColumns(const Vec3& c0, const Vec3& c1, const Vec3& c2) {
        Mat3 result;
        result.m[0] = c0.x; result.m[1] = c0.y; result.m[2] = c0.z;
        result.m[3] = c1.x; result.m[4] = c1.y; result.m[5] = c1.z;
        result.m[6] = c2.x; result.m[7] = c2.y; result.m[8] = c2.z;
        return result;
    }

    Vec3 operator*(const Vec3& v) const {
        return Vec3(m[0] * v.x + m[3] * v.y + m[6] * v.z,
                    m[1] * v.x + m[4] * v.y + m[7] * v.z,
                    m[2] * v.x + m[5] * v.y + m[8] * v.z);
    }

    Mat3 operator*(const Mat3& other) const {
        Mat3 result;
        for (u32 column = 0; column < 3; ++column) {
            for (u32 row = 0; row < 3; ++row) {
                result.at(row, column) = at(row, 0) * other.at(0, column) + at(row, 1) * other.at(1, column) +
                                         at(row, 2) * other.at(2, column);
            }
        }
        return result;
    }

    Mat3 transposed() const {
        Mat3 result;
        for (u32 row = 0; row < 3; ++row) {
            for (u32 column = 0; column < 3; ++column) {
                result.at(row, column) = at(column, row);
            }
        }
        return result;
    }

    f32 determinant() const {
        return m[0] * (m[4] * m[8] - m[7] * m[5]) - m[3] * (m[1] * m[8] - m[7] * m[2]) +
               m[6] * (m[1] * m[5] - m[4] * m[2]);
    }
};

}
