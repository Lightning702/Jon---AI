#include "JonOfflineBrain.hpp"

#include "../../engine/math/Random.hpp"
#include "../../engine/math/Scalar.hpp"

#include <cstdio>

namespace sf {
namespace {

std::string formatted(const char* pattern, f64 value) {
    char buffer[320];
    std::snprintf(buffer, sizeof(buffer), pattern, value);
    return buffer;
}

std::string formattedText(const char* pattern, const char* value) {
    char buffer[320];
    std::snprintf(buffer, sizeof(buffer), pattern, value);
    return buffer;
}

bool containsWord(const std::string& haystack, const char* needle) {
    std::string lowered;
    lowered.reserve(haystack.size());
    for (char character : haystack) {
        lowered += (character >= 'A' && character <= 'Z') ? static_cast<char>(character - 'A' + 'a') : character;
    }
    return lowered.find(needle) != std::string::npos;
}

}

void JonOfflineBrain::reset(u64 seed) {
    randomSeed = seed == 0 ? 1 : seed;
    rememberedDiscoveries.clear();
    cooldowns.clear();
    exchanges = 0;
}

void JonOfflineBrain::advanceCooldowns(f64 stepSeconds) {
    for (auto& entry : cooldowns) {
        entry.second = maxValue(entry.second - stepSeconds, 0.0);
    }
}

bool JonOfflineBrain::shouldRepeat(const std::string& key, f64 minimumIntervalSeconds) {
    for (auto& entry : cooldowns) {
        if (entry.first != key) continue;
        if (entry.second > 0.0) return false;
        entry.second = minimumIntervalSeconds;
        return true;
    }
    cooldowns.emplace_back(key, minimumIntervalSeconds);
    return true;
}

std::vector<JonUtterance> JonOfflineBrain::evaluateThreats(const JonWorldContext& context, f64 stepSeconds) {
    advanceCooldowns(stepSeconds);
    std::vector<JonUtterance> messages;

    if (context.hullIntegrity < 0.25 && shouldRepeat("hull", 20.0)) {
        messages.push_back({formatted("Rumpf bei %.0f Prozent. Ich wuerde jetzt nicht weiter beschleunigen.",
                                      context.hullIntegrity * 100.0),
                            JonUrgency::Critical, 9.0, false});
    } else if (context.hullIntegrity < 0.55 && shouldRepeat("hullWarn", 45.0)) {
        messages.push_back({formatted("Rumpf bei %.0f Prozent. Eine Werft waere keine schlechte Idee.",
                                      context.hullIntegrity * 100.0),
                            JonUrgency::Warning, 8.0, false});
    }

    const f64 fuelFraction = context.fuelKilograms / maxValue(context.fuelCapacity, 1.0);
    if (fuelFraction < 0.10 && shouldRepeat("fuel", 30.0)) {
        messages.push_back({formatted("Treibstoff bei %.0f Prozent. Ab hier ist jeder Sprung eine Einbahnstrasse.",
                                      fuelFraction * 100.0),
                            JonUrgency::Warning, 9.0, false});
    }

    if (context.heatFraction > 1.1 && shouldRepeat("heat", 18.0)) {
        messages.push_back({"Radiatoren sind ueberlastet. Energie von den Waffen wegnehmen, das reicht meistens.",
                            JonUrgency::Caution, 7.0, false});
    }

    if (context.oxygenFraction < 0.22 && shouldRepeat("oxygen", 25.0)) {
        messages.push_back({formatted("Sauerstoff bei %.0f Prozent. Zurueck ins Schiff oder Anzug nachfuellen.",
                                      context.oxygenFraction * 100.0),
                            JonUrgency::Critical, 9.0, false});
    }

    if (context.radiationSieverts > 0.6 && shouldRepeat("radiation", 30.0)) {
        messages.push_back({formatted("Strahlung bei %.2f Sievert. Ohne Abschirmung hast du hier Minuten, keine Stunden.",
                                      context.radiationSieverts),
                            JonUrgency::Warning, 8.0, false});
    }

    if (context.tidalStress > 0.02 && shouldRepeat("tidal", 12.0)) {
        messages.push_back({"Gezeitenkraefte greifen den Rumpf an. Der Unterschied zwischen Bug und Heck ist messbar.",
                            JonUrgency::Critical, 9.0, false});
    }

    if (context.voidZone == VoidZone::Ergosphere && shouldRepeat("ergosphere", 60.0)) {
        messages.push_back({formatted("Wir sind in der Ergosphaere. Deine Uhr geht jetzt mit Faktor %.4f gegen die Weltzeit.",
                                      context.timeDilation),
                            JonUrgency::Warning, 10.0, false});
    } else if (context.voidZone == VoidZone::Distortion && shouldRepeat("distortion", 60.0)) {
        messages.push_back({"Verzerrungszone. Den Instrumenten glaube ich hier nur noch zur Haelfte.",
                            JonUrgency::Caution, 8.0, false});
    } else if (context.voidZone == VoidZone::HorizonProximity && shouldRepeat("horizon", 25.0)) {
        messages.push_back({context.voidDriveInstalled
                                ? "Horizontnaehe. Der Void-Antrieb ist das Einzige, was uns hier noch rausbringt."
                                : "Horizontnaehe ohne Void-Antrieb. Ich sage es einmal deutlich: umkehren.",
                            JonUrgency::Critical, 12.0, false});
    }

    if (context.communicationBlackout && shouldRepeat("blackout", 20.0)) {
        messages.push_back({"Ionisationsblackout. Ab jetzt bin ich deine einzige Stimme.", JonUrgency::Notice, 6.0,
                            false});
    }

    if (context.shieldCharge < 0.15 && shouldRepeat("shield", 15.0)) {
        messages.push_back({"Schilde sind praktisch leer. Vier Sekunden ohne Treffer, dann laden sie wieder.",
                            JonUrgency::Warning, 7.0, false});
    }

    return messages;
}

JonUtterance JonOfflineBrain::analysePlanet(const JonWorldContext& context) const {
    ++exchanges;
    JonUtterance utterance;
    utterance.urgency = JonUrgency::Notice;
    utterance.lifetimeSeconds = 12.0;

    char buffer[600];
    if (context.habitability > 0.55) {
        std::snprintf(buffer, sizeof(buffer),
                      "%s ist %s, Bewohnbarkeit %.2f, %.0f Kelvin, %.2f g. Du koenntest hier ohne Helm rausgehen.",
                      context.nearestBodyName.c_str(), context.planetClass.c_str(), context.habitability,
                      context.surfaceTemperatureKelvin, context.surfaceGravity / 9.81);
    } else if (context.habitability > 0.15) {
        std::snprintf(buffer, sizeof(buffer),
                      "%s ist %s, %.0f Kelvin, %.2f g, Strahlung %.2f Sv. Anzug an, aber machbar.",
                      context.nearestBodyName.c_str(), context.planetClass.c_str(),
                      context.surfaceTemperatureKelvin, context.surfaceGravity / 9.81, context.radiationSieverts);
    } else {
        std::snprintf(buffer, sizeof(buffer),
                      "%s ist %s. %.0f Kelvin, %.2f g, Strahlung %.2f Sv. Landen ja, bleiben nein.",
                      context.nearestBodyName.c_str(), context.planetClass.c_str(),
                      context.surfaceTemperatureKelvin, context.surfaceGravity / 9.81, context.radiationSieverts);
    }
    utterance.text = buffer;
    return utterance;
}

std::string JonOfflineBrain::recommendLandingSite(const JonWorldContext& context) const {
    if (context.surfaceGravity > 18.0) {
        return "Bei dieser Schwerkraft empfehle ich einen Aequatorplateau-Anflug, flacher Winkel, halbe Sinkrate.";
    }
    if (context.surfaceTemperatureKelvin > 360.0) {
        return "Nachtseite anfliegen. Die Temperaturdifferenz spart dir die halbe Hitzelast.";
    }
    if (context.radiationSieverts > 0.5) {
        return "Ein Krater mit hohem Wall schirmt gut ab. Ich habe drei Kandidaten markiert.";
    }
    return "Kuestenlinie am Terminator: stabiler Untergrund, Wasser in Reichweite, milde Winde.";
}

std::string JonOfflineBrain::navigationAdvice(const JonWorldContext& context) const {
    switch (context.voidZone) {
        case VoidZone::HorizonProximity:
            return "Voller Schub entlang der Spinachse. Alles andere kostet dich mehr Delta-v als du hast.";
        case VoidZone::Ergosphere:
            return "Mit der Rotationsrichtung fliegen, nicht dagegen. Das Frame-Dragging arbeitet dann fuer dich.";
        case VoidZone::Distortion:
            return "Traegheitsnavigation nutzen. Die Sternpeilung ist hier um bis zu vier Grad verzogen.";
        case VoidZone::GravityDrift:
            return "Leichter Bahnzug nach innen. Alle zwei Minuten korrigieren, dann bleibt der Kurs sauber.";
        default:
            return "Kurs ist frei. Ich halte die Peilung stabil.";
    }
}

JonUtterance JonOfflineBrain::explainDiscovery(const std::string& subject, const JonWorldContext& context) const {
    ++exchanges;
    JonUtterance utterance;
    utterance.urgency = JonUrgency::Notice;
    utterance.lifetimeSeconds = 11.0;
    if (containsWord(subject, "void") || containsWord(subject, "chronon")) {
        utterance.text = formattedText("%s traegt eine Signatur, die nur nahe am Horizont entsteht. "
                                       "Forschungslabor Stufe 3 kann sie aufschluesseln.",
                                       subject.c_str());
    } else if (containsWord(subject, "ruine") || containsWord(subject, "vorlaeufer")) {
        utterance.text = formattedText("%s: Vorlaeufer-Bauweise, keine Nahtstellen, kein Verschleiss. "
                                       "Sie haben nicht gebaut, sie haben gefaltet.",
                                       subject.c_str());
    } else {
        utterance.text = formattedText("%s ist neu im Katalog. Ich habe es unter deinem Namen eingetragen.",
                                       subject.c_str());
    }
    if (context.discoveredStations > 0) {
        utterance.text += " Passt zu dem, was wir auf den Void-Stationen gefunden haben.";
    }
    return utterance;
}

JonUtterance JonOfflineBrain::respondToMessage(const std::string& message, const JonWorldContext& context) const {
    ++exchanges;
    JonUtterance utterance;
    utterance.urgency = JonUrgency::Ambient;
    utterance.lifetimeSeconds = 10.0;

    if (containsWord(message, "landen") || containsWord(message, "landeplatz")) {
        utterance.text = recommendLandingSite(context);
    } else if (containsWord(message, "kurs") || containsWord(message, "navig") || containsWord(message, "route")) {
        utterance.text = navigationAdvice(context);
    } else if (containsWord(message, "planet") || containsWord(message, "analyse") || containsWord(message, "scan")) {
        utterance.text = analysePlanet(context).text;
    } else if (containsWord(message, "gefahr") || containsWord(message, "sicher")) {
        utterance.text = context.voidZone == VoidZone::FarField
                             ? "Nichts Akutes. Rumpf, Schilde und Treibstoff sind im gruenen Bereich."
                             : formattedText("Wir sind in Zone %s. Das ist die Gefahr.",
                                             VoidHeart::zoneName(context.voidZone));
    } else if (containsWord(message, "zeit") || containsWord(message, "dilat")) {
        utterance.text = formatted("Dein Zeitfaktor liegt bei %.4f. Draussen vergeht die Zeit entsprechend schneller.",
                                   context.timeDilation);
    } else if (containsWord(message, "tempo") || containsWord(message, "geschwindig")) {
        utterance.text = formatted("Wir liegen bei %.4f Lichtgeschwindigkeit. Bremsweg entsprechend einplanen.",
                                   context.speedMetresPerSecond / kSpeedOfLight);
    } else if (containsWord(message, "treibstoff") || containsWord(message, "tank")) {
        utterance.text = formatted("%.0f Kilogramm im Tank. Fuer einen Sprung reicht das, fuer zwei nicht immer.",
                                   context.fuelKilograms);
    } else if (containsWord(message, "danke")) {
        utterance.text = "Dafuer bin ich da. Meistens.";
    } else if (containsWord(message, "hallo") || containsWord(message, "jon")) {
        utterance.text = rememberedDiscoveries.empty()
                             ? "Ich bin da. Sag mir, worauf du hinauswillst."
                             : formattedText("Ich bin da. Wir haben zuletzt %s katalogisiert.",
                                             rememberedDiscoveries.back().c_str());
    } else {
        utterance.text = "Dazu habe ich offline keine belastbaren Daten. Frag mich nach Kurs, Planet, Gefahr oder Zeit.";
    }
    return utterance;
}

JonMissionOffer JonOfflineBrain::generateMission(const JonWorldContext& context, u64 salt) const {
    Random random(hashCombine(randomSeed, salt));
    JonMissionOffer offer;

    const i32 kind = random.rangeInt(0, 5);
    switch (kind) {
        case 0:
            offer.title = "NOTRUF";
            offer.description = "Ein Frachter sendet auf einer alten Bergungsfrequenz. Kein Bildsignal.";
            offer.objective = "Signalquelle im System " + context.systemName + " lokalisieren und andocken";
            offer.difficulty = 2;
            break;
        case 1:
            offer.title = "KARTIERUNG";
            offer.description = "Die Oberflaeche von " + context.nearestBodyName + " ist unvollstaendig erfasst.";
            offer.objective = "Vier Oberflaechenscans in unterschiedlichen Biomen abschliessen";
            offer.difficulty = 1;
            break;
        case 2:
            offer.title = "BERGUNG";
            offer.description = "Ein Wrackfeld treibt seit Jahrzehnten in einer stabilen Bahn.";
            offer.objective = "Drei intakte Module bergen und zur naechsten Station bringen";
            offer.difficulty = 2;
            break;
        case 3:
            offer.title = "FORSCHUNGSZIEL";
            offer.description = "Eine Anomalie im Magnetfeld passt zu keiner bekannten Quelle.";
            offer.objective = "Tiefenscan mit Frequenzabstimmung ueber 90 Prozent Lockqualitaet";
            offer.difficulty = 3;
            break;
        default:
            offer.title = "PROBENREIHE";
            offer.description = "Das Labor braucht Material aus einer Zone mit erhoehter Zeitrate.";
            offer.objective = "Zwei Chronon-Proben aus der Verzerrungszone bergen";
            offer.difficulty = 4;
            break;
    }
    offer.rewardCredits = 2400.0 * static_cast<f64>(offer.difficulty) * random.rangeDouble(0.8, 1.5);
    return offer;
}

void JonOfflineBrain::rememberDiscovery(const std::string& name) {
    if (name.empty()) return;
    for (const std::string& existing : rememberedDiscoveries) {
        if (existing == name) return;
    }
    rememberedDiscoveries.push_back(name);
    if (rememberedDiscoveries.size() > 64) rememberedDiscoveries.erase(rememberedDiscoveries.begin());
}

}
