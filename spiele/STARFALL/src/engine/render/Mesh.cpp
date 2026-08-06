#include "Mesh.hpp"

namespace sf {

void FullscreenTriangle::initialize() {
    if (vertexArray != 0) return;
    gl().genVertexArrays(1, &vertexArray);
}

void FullscreenTriangle::release() {
    if (vertexArray == 0) return;
    gl().deleteVertexArrays(1, &vertexArray);
    vertexArray = 0;
}

void FullscreenTriangle::draw() const {
    if (vertexArray == 0) return;
    GLApi& api = gl();
    api.bindVertexArray(vertexArray);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    api.bindVertexArray(0);
}

}
