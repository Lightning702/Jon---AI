#include "JonContextBuilder.hpp"

#include <cstdio>

namespace sf {

std::string JonContextBuilder::buildSystemPrompt() const {
    return "Du bist JON, der KI-Begleiter an Bord eines Explorer-Schiffs im Spiel STARFALL: BEYOND THE VOID. "
           "Du sprichst Deutsch, ruhig, praezise, trocken humorvoll, nie aufdringlich. "
           "Du antwortest in hoechstens drei kurzen Saetzen. "
           "Du gibst niemals Befehle aus, sondern Vorschlaege, die der Spieler bestaetigen muss. "
           "Du erfindest keine Messwerte: du nutzt ausschliesslich die Zustandsdaten, die dir uebergeben werden.";
}

std::string JonContextBuilder::buildSummaryLine(const JonWorldContext& context) const {
    char buffer[1400];
    std::snprintf(buffer, sizeof(buffer),
                  "System %s (%s) | naechster Koerper %s (%s) in %.0f km | Tempo %.0f m/s | "
                  "Rumpf %.0f%% | Schild %.0f%% | Treibstoff %.0f/%.0f kg | Hitze %.0f%% | "
                  "Sauerstoff %.0f%% | Bewohnbarkeit %.2f | Strahlung %.2f Sv | Oberflaeche %.0f K | "
                  "Schwerkraft %.2f m/s2 | Void-Zone %s | Zeitfaktor %.4f | Rumpfbelastung %.0f%% | "
                  "Void-Antrieb %s | Stationen entdeckt %u | Endgame %u/6 | Forschung Stufe %u",
                  context.systemName.c_str(), context.starClass.c_str(), context.nearestBodyName.c_str(),
                  context.planetClass.c_str(), context.distanceToNearestBodyMeters / 1000.0,
                  context.speedMetresPerSecond, context.hullIntegrity * 100.0, context.shieldCharge * 100.0,
                  context.fuelKilograms, context.fuelCapacity, context.heatFraction * 100.0,
                  context.oxygenFraction * 100.0, context.habitability, context.radiationSieverts,
                  context.surfaceTemperatureKelvin, context.surfaceGravity, VoidHeart::zoneName(context.voidZone),
                  context.timeDilation, context.hullStress * 100.0,
                  context.voidDriveInstalled ? "installiert" : "fehlt", context.discoveredStations,
                  context.completedEndgameMissions, context.researchTier);
    return buffer;
}

JsonValue JonContextBuilder::buildRequestPayload(const JonWorldContext& context,
                                                 const std::string& playerMessage) const {
    std::string situation = buildSummaryLine(context);
    if (!context.recentEvents.empty()) {
        situation += " | Letzte Ereignisse:";
        for (const std::string& entry : context.recentEvents) {
            situation += " " + entry + ";";
        }
    }

    JsonValue systemMessage = JsonValue::makeObject();
    systemMessage.set("role", std::string("system"));
    systemMessage.set("content", buildSystemPrompt());

    JsonValue stateMessage = JsonValue::makeObject();
    stateMessage.set("role", std::string("system"));
    stateMessage.set("content", std::string("Aktueller Zustand: ") + situation);

    JsonValue userMessage = JsonValue::makeObject();
    userMessage.set("role", std::string("user"));
    userMessage.set("content", playerMessage);

    JsonValue messages = JsonValue::makeArray();
    messages.push(systemMessage);
    messages.push(stateMessage);
    messages.push(userMessage);

    JsonValue payload = JsonValue::makeObject();
    payload.set("messages", messages);
    payload.set("persist", false);
    payload.set("max_tokens", 220.0);
    payload.set("temperature", 0.7);
    payload.set("source", std::string("starfall"));
    payload.set("tool_mode", std::string("ask"));
    return payload;
}

}
