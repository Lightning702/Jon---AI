#pragma once

#include "GLApi.hpp"

namespace sf {

class FullscreenTriangle {
public:
    void initialize();
    void release();
    void draw() const;

private:
    GLuint vertexArray = 0;
};

}
