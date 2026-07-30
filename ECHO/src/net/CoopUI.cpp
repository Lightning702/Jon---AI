#include "CoopUI.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

namespace {
const Vec4 kInk(0.94f, 0.94f, 0.96f, 1.0f);
const Vec4 kGold(0.98f, 0.84f, 0.46f, 1.0f);
const Vec4 kCyan(0.44f, 0.90f, 1.0f, 1.0f);
const Vec4 kGreen(0.58f, 0.94f, 0.66f, 1.0f);
const Vec4 kRed(0.98f, 0.58f, 0.56f, 1.0f);
const Vec4 kDim(0.62f, 0.66f, 0.72f, 1.0f);

enum CoopAction {
    ACT_NONE = 0,
    ACT_HOST,
    ACT_JOIN_VIEW,
    ACT_JOIN_GO,
    ACT_BACK,
    ACT_CLOSE,
    ACT_READY,
    ACT_START,
    ACT_LEAVE,
    ACT_KILL,
    ACT_NAME,
    ACT_NAME_OK,
    ACT_RETRY
};

const int kHomeItems[] = { ACT_HOST, ACT_JOIN_VIEW, ACT_NAME, ACT_CLOSE };
const int kHomeCount = 4;
}

void CoopMenu::init(CoopSession* session, Window* win, UIRenderer* renderer, AudioEngine* engine) {
    coop = session;
    window = win;
    ui = renderer;
    audio = engine;
    view = CVIEW_HOME;
    index = 0;
    shown = false;
}

void CoopMenu::open() {
    shown = true;
    hits.clear();
    inputGuard = 0.22f;
    index = 0;
    hoverAction = 0;
    launchRequested = false;
    exitRequested = false;
    editingName = false;
    if (coop != nullptr && coop->inSession()) view = CVIEW_LOBBY;
    else view = CVIEW_HOME;
    if (window != nullptr) window->setCursorLocked(false);
}

void CoopMenu::close() {
    shown = false;
    hits.clear();
    editingName = false;
}

bool CoopMenu::consumeLaunch() {
    if (!launchRequested) return false;
    launchRequested = false;
    return true;
}

bool CoopMenu::consumeExit() {
    if (!exitRequested) return false;
    exitRequested = false;
    return true;
}

void CoopMenu::pushHit(float x, float y, float w, float h, int action) {
    Hit hit;
    hit.x = x; hit.y = y; hit.w = w; hit.h = h;
    hit.action = action;
    hits.push_back(hit);
}

void CoopMenu::typeInto(std::string& target, size_t maxLen, bool codeMode) {
    Input& in = window->input();
    const std::string& typed = in.textInput();
    for (size_t i = 0; i < typed.size(); i++) {
        unsigned char c = (unsigned char)typed[i];
        if (c == 8) {
            if (!target.empty()) target.pop_back();
            continue;
        }
        if (c < 32) continue;
        if (target.size() >= maxLen) continue;
        if (codeMode) {
            if (c >= 'a' && c <= 'z') c = (unsigned char)(c - 32);
            bool alnum = (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9');
            bool extra = c == '@' || c == '.' || c == ':' || c == '-' || c == '_';
            if (!alnum && !extra) continue;
        }
        target.push_back((char)c);
    }
    if (in.keyPressed(KEY_BACKSPACE) && !target.empty() && typed.empty()) target.pop_back();
}

void CoopMenu::activate(int action) {
    if (coop == nullptr) return;
    if (audio != nullptr) audio->play2D(SFX_SWITCH, 0.24f, 1.1f);

    switch (action) {
    case ACT_HOST:
        coop->hostGame(playerName, (u64)(GetTickCount64() & 0x7FFFFFFFULL), Vec3(0, 0, 0));
        view = CVIEW_LOBBY;
        break;
    case ACT_JOIN_VIEW:
        view = CVIEW_JOIN;
        codeInput.clear();
        break;
    case ACT_JOIN_GO:
        if (codeInput.size() >= 6) {
            coop->joinGame(codeInput, playerName);
            view = CVIEW_LOBBY;
        }
        break;
    case ACT_NAME:
        editingName = true;
        view = CVIEW_NAME;
        break;
    case ACT_NAME_OK:
        editingName = false;
        if (playerName.empty()) playerName = "Spieler";
        view = CVIEW_HOME;
        break;
    case ACT_READY: {
        bool ready = false;
        const std::vector<CoopMember>& members = coop->members();
        for (size_t i = 0; i < members.size(); i++) {
            if (members[i].id == coop->localId()) ready = members[i].ready;
        }
        coop->setReady(!ready);
        break;
    }
    case ACT_START:
        coop->requestStart();
        break;
    case ACT_KILL:
        coop->closeLobby();
        coop->leave();
        view = CVIEW_HOME;
        break;
    case ACT_LEAVE:
        coop->leave();
        view = CVIEW_HOME;
        break;
    case ACT_RETRY:
        view = CVIEW_HOME;
        break;
    case ACT_BACK:
        view = CVIEW_HOME;
        break;
    case ACT_CLOSE:
        exitRequested = true;
        close();
        break;
    default:
        break;
    }
}

void CoopMenu::update(float dt) {
    if (!shown || coop == nullptr || window == nullptr) return;
    blink += dt;
    if (inputGuard > 0.0f) {
        inputGuard -= dt;
        return;
    }

    int phase = coop->phase();
    if (phase == COOP_PLAYING) {
        launchRequested = true;
        close();
        return;
    }
    if (phase == COOP_ERROR) view = CVIEW_PROBLEM;
    else if (phase == COOP_LOADING || phase == COOP_LOST || phase == COOP_CONNECTING) view = CVIEW_WAIT;
    else if (phase == COOP_LOBBY) view = CVIEW_LOBBY;

    Input& in = window->input();

    if (view == CVIEW_JOIN) typeInto(codeInput, 24, true);
    if (view == CVIEW_NAME) typeInto(playerName, 18, false);

    Vec2 mouse = in.mousePos();
    bool moved = lengthSq(mouse - lastMouse) > 1.0f;
    lastMouse = mouse;
    hoverAction = ACT_NONE;
    for (size_t i = 0; i < hits.size(); i++) {
        const Hit& hit = hits[i];
        if (mouse.x < hit.x || mouse.x > hit.x + hit.w) continue;
        if (mouse.y < hit.y || mouse.y > hit.y + hit.h) continue;
        hoverAction = hit.action;
        if (in.mousePressed(MOUSE_LEFT)) {
            activate(hit.action);
            return;
        }
    }
    (void)moved;

    if (view == CVIEW_HOME) {
        if (in.keyPressed(KEY_DOWN) || in.keyPressed(KEY_S)) index = (index + 1) % kHomeCount;
        if (in.keyPressed(KEY_UP) || in.keyPressed(KEY_W)) index = (index + kHomeCount - 1) % kHomeCount;
        if (in.keyPressed(KEY_ENTER)) activate(kHomeItems[index]);
    } else if (view == CVIEW_JOIN) {
        if (in.keyPressed(KEY_ENTER)) activate(ACT_JOIN_GO);
    } else if (view == CVIEW_NAME) {
        if (in.keyPressed(KEY_ENTER)) activate(ACT_NAME_OK);
    } else if (view == CVIEW_LOBBY) {
        if (in.keyPressed(KEY_ENTER)) activate(coop->isHost() ? ACT_START : ACT_READY);
    } else if (view == CVIEW_PROBLEM) {
        if (in.keyPressed(KEY_ENTER)) activate(ACT_RETRY);
    }

    if (in.keyPressed(KEY_ESCAPE)) {
        if (view == CVIEW_JOIN || view == CVIEW_NAME || view == CVIEW_PROBLEM) view = CVIEW_HOME;
        else if (view == CVIEW_LOBBY || view == CVIEW_WAIT) close();
        else activate(ACT_CLOSE);
    }

    std::string line;
    while (coop->consumeChat(line)) {
        for (int i = 3; i > 0; i--) {
            chatFeed[i] = chatFeed[i - 1];
            chatTimer[i] = chatTimer[i - 1];
        }
        chatFeed[0] = line;
        chatTimer[0] = 9.0f;
    }
    for (int i = 0; i < 4; i++) {
        if (chatTimer[i] > 0.0f) chatTimer[i] -= dt;
    }
}

void CoopMenu::panel(float x, float y, float w, float h, float alpha) {
    ui->rect(x, y, w, h, Vec4(0.035f, 0.042f, 0.058f, 0.90f * alpha));
    ui->rectOutline(x, y, w, h, 1.6f, Vec4(kGold.x, kGold.y, kGold.z, 0.30f * alpha));
}

void CoopMenu::heading(const std::string& text, const std::string& sub, float x, float y, float w, float h) {
    ui->textShadow(text, x, y, h * 0.036f, kGold, ALIGN_LEFT, h * 0.008f);
    if (!sub.empty()) {
        ui->text(sub, x, y + h * 0.048f, h * 0.019f, Vec4(kDim.x, kDim.y, kDim.z, 0.9f), ALIGN_LEFT);
    }
}

void CoopMenu::draw(float time) {
    if (!shown || coop == nullptr || ui == nullptr) return;
    hits.clear();

    float w = (float)ui->width(), h = (float)ui->height();
    ui->rect(0, 0, w, h, Vec4(0.01f, 0.014f, 0.022f, 0.88f));

    float panelW = std::min(w * 0.62f, h * 1.15f);
    float panelH = h * 0.72f;
    float px = (w - panelW) * 0.5f;
    float py = (h - panelH) * 0.5f;
    panel(px, py, panelW, panelH, 1.0f);

    float x = px + h * 0.045f;
    float y = py + h * 0.05f;
    float itemH = h * 0.062f;
    float rowW = panelW - h * 0.09f;

    if (view == CVIEW_HOME) {
        heading("ONLINE KOOP", "Zwei Reisende, eine Welt. Verbindung ueber Freundschaftscode.", x, y, rowW, h);
        float ry = y + h * 0.115f;
        const char* labels[] = { "SPIEL ERSTELLEN", "SPIEL BEITRETEN", "NAME AENDERN", "ZURUECK" };
        const char* hints[] = {
            "Server legt eine Lobby an und nennt dir den Code",
            "Code des Gastgebers eingeben",
            "",
            "Zurueck ins Menue"
        };
        for (int i = 0; i < kHomeCount; i++) {
            bool active = index == i || hoverAction == kHomeItems[i];
            ui->rect(x, ry, rowW, itemH, Vec4(1, 1, 1, active ? 0.085f : 0.032f));
            if (active) ui->rect(x, ry, h * 0.004f, itemH, kGold);
            ui->textShadow(labels[i], x + h * 0.022f + (active ? h * 0.006f : 0.0f), ry + itemH * 0.28f,
                           h * 0.026f, active ? kInk : Vec4(kInk.x, kInk.y, kInk.z, 0.78f), ALIGN_LEFT);
            std::string hint = hints[i];
            if (i == 2) hint = "Aktuell: " + playerName;
            if (!hint.empty()) {
                ui->text(hint, x + h * 0.022f, ry + itemH * 0.66f, h * 0.016f,
                         Vec4(kDim.x, kDim.y, kDim.z, 0.72f), ALIGN_LEFT);
            }
            pushHit(x, ry, rowW, itemH, kHomeItems[i]);
            ry += itemH + h * 0.012f;
        }
        char buf[160];
        std::snprintf(buf, sizeof(buf), "Server %s:%d   —   fuer Internet-Spiele Portfreigabe oder oeffentlichen Jon-Server nutzen",
                      coop->serverHost().c_str(), coop->serverPort());
        ui->text(buf, x, py + panelH - h * 0.038f, h * 0.016f, Vec4(kDim.x, kDim.y, kDim.z, 0.65f), ALIGN_LEFT);
        return;
    }

    if (view == CVIEW_JOIN || view == CVIEW_NAME) {
        bool codeMode = view == CVIEW_JOIN;
        heading(codeMode ? "SPIEL BEITRETEN" : "NAME AENDERN",
                codeMode ? "Erlaubt: AB39KD oder AB39KD@server:8759" : "So sehen dich die anderen im Spiel.",
                x, y, rowW, h);
        float boxY = y + h * 0.14f;
        ui->rect(x, boxY, rowW, h * 0.085f, Vec4(0.02f, 0.024f, 0.034f, 0.95f));
        ui->rectOutline(x, boxY, rowW, h * 0.085f, 1.6f, Vec4(kCyan.x, kCyan.y, kCyan.z, 0.55f));
        std::string shownText = codeMode ? codeInput : playerName;
        bool caret = std::fmod(blink, 1.0f) < 0.55f;
        ui->textShadow(shownText + (caret ? "|" : " "), x + h * 0.020f, boxY + h * 0.024f,
                       codeMode ? h * 0.042f : h * 0.032f, kInk, ALIGN_LEFT, codeMode ? h * 0.012f : h * 0.002f);
        if (shownText.empty()) {
            ui->text(codeMode ? "AB39KD" : "Spieler", x + h * 0.020f, boxY + h * 0.030f,
                     h * 0.030f, Vec4(kDim.x, kDim.y, kDim.z, 0.35f), ALIGN_LEFT, h * 0.010f);
        }

        float by = boxY + h * 0.125f;
        float halfW = rowW * 0.48f;
        bool okHover = hoverAction == (codeMode ? ACT_JOIN_GO : ACT_NAME_OK);
        ui->rect(x, by, halfW, itemH, Vec4(kGreen.x, kGreen.y, kGreen.z, okHover ? 0.28f : 0.14f));
        ui->text(codeMode ? "VERBINDEN" : "UEBERNEHMEN", x + halfW * 0.5f, by + itemH * 0.34f,
                 h * 0.024f, kGreen, ALIGN_CENTER, h * 0.005f);
        pushHit(x, by, halfW, itemH, codeMode ? ACT_JOIN_GO : ACT_NAME_OK);

        float bx2 = x + rowW - halfW;
        bool backHover = hoverAction == ACT_BACK;
        ui->rect(bx2, by, halfW, itemH, Vec4(1, 1, 1, backHover ? 0.10f : 0.04f));
        ui->text("ZURUECK", bx2 + halfW * 0.5f, by + itemH * 0.34f, h * 0.024f,
                 Vec4(kInk.x, kInk.y, kInk.z, 0.8f), ALIGN_CENTER, h * 0.005f);
        pushHit(bx2, by, halfW, itemH, ACT_BACK);

        ui->text("ENTER bestaetigt, ESC geht zurueck", x, py + panelH - h * 0.038f, h * 0.016f,
                 Vec4(kDim.x, kDim.y, kDim.z, 0.6f), ALIGN_LEFT);
        return;
    }

    if (view == CVIEW_WAIT) {
        heading("SYNCHRONISIERE", coop->statusText(), x, y, rowW, h);
        float ring = y + h * 0.20f;
        float frac = std::fmod(time * 0.6f, 1.0f);
        ui->ring(px + panelW * 0.5f, ring, h * 0.055f, h * 0.008f, frac, kCyan);
        ui->text("Beide Spieler starten gleichzeitig, sobald jeder geladen hat.",
                 px + panelW * 0.5f, ring + h * 0.10f, h * 0.019f,
                 Vec4(kDim.x, kDim.y, kDim.z, 0.85f), ALIGN_CENTER);
        float by = py + panelH - h * 0.10f;
        ui->rect(x, by, rowW * 0.4f, itemH, Vec4(kRed.x, kRed.y, kRed.z, hoverAction == ACT_LEAVE ? 0.26f : 0.12f));
        ui->text("ABBRECHEN", x + rowW * 0.2f, by + itemH * 0.34f, h * 0.024f, kRed, ALIGN_CENTER, h * 0.005f);
        pushHit(x, by, rowW * 0.4f, itemH, ACT_LEAVE);
        return;
    }

    if (view == CVIEW_PROBLEM) {
        heading("VERBINDUNG FEHLGESCHLAGEN", coop->errorText(), x, y, rowW, h);
        float by = y + h * 0.18f;
        ui->rect(x, by, rowW * 0.45f, itemH, Vec4(1, 1, 1, hoverAction == ACT_RETRY ? 0.11f : 0.045f));
        ui->text("ZURUECK ZUM MENUE", x + rowW * 0.225f, by + itemH * 0.34f, h * 0.023f, kInk, ALIGN_CENTER, h * 0.004f);
        pushHit(x, by, rowW * 0.45f, itemH, ACT_RETRY);
        ui->text("Pruefe Adresse und Portfreigabe. Der Gastgeber muss Jon laufen haben.",
                 x, by + itemH + h * 0.02f, h * 0.017f, Vec4(kDim.x, kDim.y, kDim.z, 0.7f), ALIGN_LEFT);
        return;
    }

    heading("LOBBY", "Gib den Code weiter. Der Gastgeber startet, wenn alle bereit sind.", x, y, rowW, h);

    float codeY = y + h * 0.115f;
    ui->rect(x, codeY, rowW, h * 0.095f, Vec4(kGold.x, kGold.y, kGold.z, 0.09f));
    ui->rectOutline(x, codeY, rowW, h * 0.095f, 1.4f, Vec4(kGold.x, kGold.y, kGold.z, 0.45f));
    ui->text("FREUNDSCHAFTSCODE", x + h * 0.020f, codeY + h * 0.014f, h * 0.015f,
             Vec4(kDim.x, kDim.y, kDim.z, 0.85f), ALIGN_LEFT, h * 0.004f);
    ui->textShadow(coop->code().empty() ? "......" : coop->code(), x + h * 0.020f, codeY + h * 0.038f,
                   h * 0.046f, kGold, ALIGN_LEFT, h * 0.016f);
    if (!coop->invite().empty()) {
        ui->text("Mit Adresse: " + coop->invite(), x + rowW - h * 0.020f, codeY + h * 0.062f,
                 h * 0.016f, Vec4(kDim.x, kDim.y, kDim.z, 0.8f), ALIGN_RIGHT);
    }

    float ry = codeY + h * 0.120f;
    const std::vector<CoopMember>& members = coop->members();
    bool everyoneReady = members.size() > 1;
    bool meReady = false;
    for (size_t i = 0; i < members.size(); i++) {
        const CoopMember& member = members[i];
        if (!member.host && !member.ready) everyoneReady = false;
        if (member.id == coop->localId()) meReady = member.ready;

        ui->rect(x, ry, rowW, itemH * 0.82f, Vec4(1, 1, 1, 0.038f));
        Vec4 dot = !member.online ? kRed : (member.ping < 90.0f ? kGreen : kGold);
        ui->circle(x + h * 0.022f, ry + itemH * 0.41f, h * 0.010f, 12, dot);
        std::string label = member.name;
        if (member.id == coop->localId()) label += "  (du)";
        ui->textShadow(label, x + h * 0.044f, ry + itemH * 0.24f, h * 0.024f, kInk, ALIGN_LEFT);
        const char* tag = !member.online ? "OFFLINE" : (member.host ? "HOST" : (member.ready ? "BEREIT" : "WAEHLT"));
        Vec4 tagCol = !member.online ? kRed : (member.host ? kGold : (member.ready ? kGreen : kDim));
        ui->text(tag, x + rowW - h * 0.130f, ry + itemH * 0.28f, h * 0.018f, tagCol, ALIGN_RIGHT, h * 0.004f);
        char pingBuf[32];
        std::snprintf(pingBuf, sizeof(pingBuf), "%d ms", (int)member.ping);
        ui->text(member.online ? pingBuf : "-", x + rowW - h * 0.020f, ry + itemH * 0.28f, h * 0.018f,
                 Vec4(kDim.x, kDim.y, kDim.z, 0.85f), ALIGN_RIGHT);
        ry += itemH * 0.82f + h * 0.010f;
    }
    if (members.size() < 2) {
        ui->rect(x, ry, rowW, itemH * 0.82f, Vec4(1, 1, 1, 0.018f));
        ui->text("Freier Platz — warte auf Beitritt", x + h * 0.044f, ry + itemH * 0.28f, h * 0.020f,
                 Vec4(kDim.x, kDim.y, kDim.z, 0.55f), ALIGN_LEFT);
        ry += itemH * 0.82f + h * 0.010f;
    }

    float by = py + panelH - h * 0.095f;
    float halfW = rowW * 0.47f;
    if (coop->isHost()) {
        bool can = everyoneReady;
        Vec4 col = can ? kGreen : kDim;
        ui->rect(x, by, halfW, itemH, Vec4(col.x, col.y, col.z, hoverAction == ACT_START ? 0.26f : 0.12f));
        ui->text(can ? "SPIEL STARTEN" : "WARTE AUF BEREIT", x + halfW * 0.5f, by + itemH * 0.34f,
                 h * 0.023f, col, ALIGN_CENTER, h * 0.004f);
        if (can) pushHit(x, by, halfW, itemH, ACT_START);
        float bx2 = x + rowW - halfW;
        ui->rect(bx2, by, halfW, itemH, Vec4(kRed.x, kRed.y, kRed.z, hoverAction == ACT_KILL ? 0.24f : 0.10f));
        ui->text("LOBBY SCHLIESSEN", bx2 + halfW * 0.5f, by + itemH * 0.34f, h * 0.023f, kRed, ALIGN_CENTER, h * 0.004f);
        pushHit(bx2, by, halfW, itemH, ACT_KILL);
    } else {
        Vec4 col = meReady ? kDim : kGreen;
        ui->rect(x, by, halfW, itemH, Vec4(col.x, col.y, col.z, hoverAction == ACT_READY ? 0.26f : 0.12f));
        ui->text(meReady ? "BEREIT ZURUECKNEHMEN" : "BEREIT", x + halfW * 0.5f, by + itemH * 0.34f,
                 h * 0.023f, col, ALIGN_CENTER, h * 0.004f);
        pushHit(x, by, halfW, itemH, ACT_READY);
        float bx2 = x + rowW - halfW;
        ui->rect(bx2, by, halfW, itemH, Vec4(kRed.x, kRed.y, kRed.z, hoverAction == ACT_LEAVE ? 0.24f : 0.10f));
        ui->text("LOBBY VERLASSEN", bx2 + halfW * 0.5f, by + itemH * 0.34f, h * 0.023f, kRed, ALIGN_CENTER, h * 0.004f);
        pushHit(bx2, by, halfW, itemH, ACT_LEAVE);
    }
}

void CoopMenu::drawHudBadge(float time) {
    if (coop == nullptr || ui == nullptr) return;
    if (!coop->inSession()) return;

    float w = (float)ui->width(), h = (float)ui->height();
    float rowH = h * 0.030f;
    float x = w - h * 0.020f;
    float y = h * 0.020f;

    const std::vector<CoopMember>& members = coop->members();
    for (size_t i = 0; i < members.size(); i++) {
        const CoopMember& member = members[i];
        Vec4 dot = !member.online ? kRed : (member.ping < 90.0f ? kGreen : kGold);
        char buf[96];
        std::snprintf(buf, sizeof(buf), "%s  %d ms", member.name.c_str(), (int)member.ping);
        float textW = h * 0.170f;
        ui->rect(x - textW, y, textW, rowH * 0.88f, Vec4(0.02f, 0.026f, 0.036f, 0.55f));
        ui->circle(x - textW + h * 0.012f, y + rowH * 0.44f, h * 0.006f, 10, dot);
        ui->text(buf, x - h * 0.010f, y + rowH * 0.24f, h * 0.017f,
                 Vec4(kInk.x, kInk.y, kInk.z, member.online ? 0.92f : 0.5f), ALIGN_RIGHT);
        y += rowH;
    }

    if (coop->phase() == COOP_LOST) {
        float pulse = 0.55f + 0.45f * std::sin(time * 6.0f);
        ui->rect(w * 0.5f - h * 0.20f, 0.0f, h * 0.40f, h * 0.040f, Vec4(0.35f, 0.05f, 0.06f, 0.85f));
        ui->text("VERBINDUNG WEG — WIEDERVERBINDEN ...", w * 0.5f, h * 0.011f, h * 0.020f,
                 Vec4(1, 0.85f, 0.85f, pulse), ALIGN_CENTER, h * 0.004f);
    }

    float cy = h * 0.72f;
    for (int i = 0; i < 4; i++) {
        if (chatTimer[i] <= 0.0f || chatFeed[i].empty()) continue;
        float a = std::min(1.0f, chatTimer[i] / 1.5f);
        ui->text(chatFeed[i], h * 0.024f, cy, h * 0.019f, Vec4(kInk.x, kInk.y, kInk.z, a * 0.85f), ALIGN_LEFT);
        cy += h * 0.026f;
    }
}

}
