#pragma once

#include "CoopSession.h"
#include "../platform/Window.h"
#include "../ui/UIRenderer.h"
#include "../audio/AudioEngine.h"

namespace echo {

enum CoopView {
    CVIEW_HOME = 0,
    CVIEW_JOIN,
    CVIEW_NAME,
    CVIEW_LOBBY,
    CVIEW_WAIT,
    CVIEW_PROBLEM
};

class CoopMenu {
public:
    void init(CoopSession* session, Window* window, UIRenderer* ui, AudioEngine* audio);
    void open();
    void close();
    bool visible() const { return shown; }
    bool blocksGameplay() const { return shown; }

    void update(float dt);
    void draw(float time);
    void drawHudBadge(float time);

    bool consumeLaunch();
    bool consumeExit();
    void setDefaultName(const std::string& name) { if (!name.empty()) playerName = name; }
    const std::string& name() const { return playerName; }

private:
    struct Hit {
        float x = 0, y = 0, w = 0, h = 0;
        int action = 0;
    };

    void pushHit(float x, float y, float w, float h, int action);
    void activate(int action);
    void typeInto(std::string& target, size_t maxLen, bool codeMode);
    void panel(float x, float y, float w, float h, float alpha);
    void heading(const std::string& text, const std::string& sub, float x, float y, float w, float h);
    int hovered() const { return hoverAction; }

    CoopSession* coop = nullptr;
    Window* window = nullptr;
    UIRenderer* ui = nullptr;
    AudioEngine* audio = nullptr;

    std::vector<Hit> hits;
    std::string codeInput;
    std::string playerName = "Spieler";
    std::string chatFeed[4];
    float chatTimer[4] = { 0, 0, 0, 0 };

    int view = CVIEW_HOME;
    int index = 0;
    int hoverAction = 0;
    int pendingAfterName = 0;
    bool shown = false;
    bool launchRequested = false;
    bool exitRequested = false;
    bool editingName = false;
    float blink = 0.0f;
    em::Vec2 lastMouse;
};

}
