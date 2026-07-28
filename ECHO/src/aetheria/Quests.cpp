#include "Quests.h"
#include "AetheriaWorld.h"

using namespace em;

namespace aeth {

namespace {

struct GatherDef {
    int flora;
    const char* plural;
    const char* single;
};

GatherDef gatherFor(int biome) {
    switch (biome) {
    case BIOME_MARSH: return { FLORA_MUSHROOM, "Leuchtpilze", "Leuchtpilz" };
    case BIOME_SNOW: return { FLORA_CRYSTAL, "Klangkristalle", "Klangkristall" };
    case BIOME_HIGHLAND: return { FLORA_CRYSTAL, "Klangkristalle", "Klangkristall" };
    case BIOME_FOREST: return { FLORA_FERN, "Silberfarn", "Silberfarn" };
    case BIOME_GOLDEN_WOOD: return { FLORA_MUSHROOM, "Leuchtpilze", "Leuchtpilz" };
    default: return { FLORA_FLOWER, "Sonnenblueten", "Sonnenbluete" };
    }
}

const char* kSpecies[] = { "Wiesenhuepfer", "Moosschleime", "Waldkobolde", "Kristallkaefer", "Nebelgeister" };

std::string numbered(const char* prefix, int n, const char* noun) {
    char buf[160];
    std::snprintf(buf, sizeof(buf), "%s %d %s", prefix, n, noun);
    return std::string(buf);
}

}

void QuestLog::clear() {
    quests.clear();
    tracked = -1;
    completed = 0;
    chainStage = 0;
}

void QuestLog::build(const AetheriaWorld& world, u64 seed) {
    clear();
    Rng rng(seed ^ 0x9E3779B97F4A7C15ULL);

    const std::vector<Settlement>& villages = world.settlements();
    const std::vector<Landmark>& marks = world.landmarks();
    int vc = (int)villages.size();
    if (vc == 0) return;

    for (int v = 0; v < vc; v++) {
        const Settlement& s = villages[(size_t)v];
        std::string giver = s.giverName;

        GatherDef g = gatherFor(s.biome);
        {
            Quest q;
            q.id = (int)quests.size();
            q.kind = QUEST_GATHER;
            q.village = v;
            q.giver = giver;
            q.place = s.name;
            q.target = g.flora;
            q.needed = rng.rangeInt(5, 9);
            q.xp = 70 + q.needed * 6;
            q.gold = 18 + q.needed * 4;
            q.marker = s.center;
            char line[220];
            std::snprintf(line, sizeof(line),
                          "Unsere Vorraete sind leer. Bring mir %d %s, dann hat das Dorf wieder etwas zu brauen.",
                          q.needed, g.plural);
            q.title = std::string("Ernte fuer ") + s.name;
            q.task = numbered("Sammle", q.needed, g.plural);
            q.offer = line;
            q.thanks = "Genau das haben wir gebraucht. Nimm das hier.";
            quests.push_back(q);
        }

        {
            Quest q;
            q.id = (int)quests.size();
            q.kind = QUEST_HUNT;
            q.village = v;
            q.giver = giver;
            q.place = s.name;
            q.target = rng.rangeInt(0, 4);
            q.needed = rng.rangeInt(3, 6);
            q.xp = 95 + q.needed * 10;
            q.gold = 30 + q.needed * 7;
            q.marker = s.center;
            q.title = "Ungebetene Gaeste";
            q.task = numbered("Vertreibe", q.needed, kSpecies[q.target]);
            q.offer = std::string("Seit Tagen streifen ") + kSpecies[q.target] +
                      " um unsere Felder. Zeig ihnen, dass hier Menschen leben.";
            q.thanks = "Die Felder sind wieder sicher. Danke dir.";
            quests.push_back(q);
        }

        if (vc > 1) {
            int dest = (v + 1 + rng.rangeInt(0, vc - 1)) % vc;
            if (dest == v) dest = (v + 1) % vc;
            const Settlement& d = villages[(size_t)dest];
            Quest q;
            q.id = (int)quests.size();
            q.kind = QUEST_TRAVEL;
            q.village = v;
            q.giver = giver;
            q.place = s.name;
            q.target = dest;
            q.needed = 1;
            q.xp = 120;
            q.gold = 45;
            q.marker = d.center;
            q.markerRadius = d.radius + 6.0f;
            q.title = std::string("Botengang nach ") + d.name;
            q.task = std::string("Bring das Siegel nach ") + d.name;
            q.offer = std::string("Dieses Siegel muss nach ") + d.name +
                      ". Der Weg ist weit, aber du siehst aus, als kaemst du herum.";
            q.thanks = "Das Siegel ist angekommen. Du bist schnell.";
            quests.push_back(q);
        }

        if (!marks.empty()) {
            int best = 0;
            float bestD = 1e18f;
            for (int i = 0; i < (int)marks.size(); i++) {
                float d = distanceSq(marks[(size_t)i].position, s.center);
                if (d < bestD) { bestD = d; best = i; }
            }
            const Landmark& lm = marks[(size_t)best];
            Quest q;
            q.id = (int)quests.size();
            q.kind = QUEST_LANDMARK;
            q.village = v;
            q.giver = giver;
            q.place = s.name;
            q.target = best;
            q.needed = 1;
            q.xp = 150;
            q.gold = 60;
            q.marker = lm.position;
            q.markerRadius = 12.0f;
            q.title = std::string("Was bei ") + lm.name + " liegt";
            q.task = std::string("Untersuche ") + lm.name;
            q.offer = std::string("Niemand geht mehr zu ") + lm.name +
                      ". Sieh dir an, was dort steht, und komm zurueck.";
            q.thanks = "Also steht es noch. Gut zu wissen.";
            quests.push_back(q);
        }
    }

    for (int i = 0; i < (int)quests.size(); i++) {
        if (quests[(size_t)i].village == 0) quests[(size_t)i].state = QUEST_OFFERED;
    }
}

void QuestLog::revealVillage(int village) {
    for (Quest& q : quests) {
        if (q.village == village && q.state == QUEST_HIDDEN) q.state = QUEST_OFFERED;
    }
}

int QuestLog::offeredFor(int village) const {
    for (int i = 0; i < (int)quests.size(); i++) {
        const Quest& q = quests[(size_t)i];
        if (q.village == village && q.state == QUEST_OFFERED) return i;
    }
    return -1;
}

int QuestLog::readyFor(int village) const {
    for (int i = 0; i < (int)quests.size(); i++) {
        const Quest& q = quests[(size_t)i];
        if (q.village == village && q.state == QUEST_READY) return i;
    }
    return -1;
}

int QuestLog::activeCount() const {
    int n = 0;
    for (const Quest& q : quests) {
        if (q.state == QUEST_ACTIVE || q.state == QUEST_READY) n++;
    }
    return n;
}

void QuestLog::accept(int index) {
    if (index < 0 || index >= (int)quests.size()) return;
    Quest& q = quests[(size_t)index];
    if (q.state != QUEST_OFFERED) return;
    q.state = QUEST_ACTIVE;
    if (tracked < 0) tracked = index;
}

bool QuestLog::complete(int index) {
    if (index < 0 || index >= (int)quests.size()) return false;
    Quest& q = quests[(size_t)index];
    if (q.state != QUEST_READY) return false;
    q.state = QUEST_DONE;
    completed++;
    if (tracked == index) {
        tracked = -1;
        cycleTracked();
    }
    advanceChain();
    return true;
}

void QuestLog::advanceChain() {
    if (quests.empty()) return;
    int villagesUnlocked = 1 + completed / 2;
    for (Quest& q : quests) {
        if (q.state == QUEST_HIDDEN && q.village <= villagesUnlocked) q.state = QUEST_OFFERED;
    }
}

bool QuestLog::reportGather(int floraType) {
    bool any = false;
    for (int i = 0; i < (int)quests.size(); i++) {
        Quest& q = quests[(size_t)i];
        if (q.state != QUEST_ACTIVE || q.kind != QUEST_GATHER || q.target != floraType) continue;
        q.progress++;
        any = true;
        if (q.progress >= q.needed) q.state = QUEST_READY;
    }
    return any;
}

bool QuestLog::reportHunt(int species) {
    bool any = false;
    for (int i = 0; i < (int)quests.size(); i++) {
        Quest& q = quests[(size_t)i];
        if (q.state != QUEST_ACTIVE || q.kind != QUEST_HUNT || q.target != species) continue;
        q.progress++;
        any = true;
        if (q.progress >= q.needed) q.state = QUEST_READY;
    }
    return any;
}

int QuestLog::checkPositions(const Vec3& player) {
    for (int i = 0; i < (int)quests.size(); i++) {
        Quest& q = quests[(size_t)i];
        if (q.state != QUEST_ACTIVE) continue;
        if (q.kind != QUEST_TRAVEL && q.kind != QUEST_LANDMARK) continue;
        if (distance(Vec2(q.marker.x, q.marker.z), Vec2(player.x, player.z)) > q.markerRadius) continue;
        q.progress = q.needed;
        q.state = QUEST_READY;
        return i;
    }
    return -1;
}

void QuestLog::cycleTracked() {
    int n = (int)quests.size();
    if (n == 0) return;
    for (int step = 1; step <= n; step++) {
        int i = ((tracked < 0 ? 0 : tracked) + step) % n;
        const Quest& q = quests[(size_t)i];
        if (q.state == QUEST_ACTIVE || q.state == QUEST_READY) {
            tracked = i;
            return;
        }
    }
    tracked = -1;
}

std::vector<std::string> QuestLog::journalLines() const {
    std::vector<std::string> out;
    char buf[220];

    out.push_back("#LAEUFT GERADE");
    int shown = 0;
    for (int i = 0; i < (int)quests.size(); i++) {
        const Quest& q = quests[(size_t)i];
        if (q.state != QUEST_ACTIVE && q.state != QUEST_READY) continue;
        shown++;

        std::snprintf(buf, sizeof(buf), "%s%s", i == tracked ? "> " : "  ", q.title.c_str());
        out.push_back(buf);

        if (q.state == QUEST_READY) {
            std::snprintf(buf, sizeof(buf), "     FERTIG - abgeben bei %s in %s", q.giver.c_str(), q.place.c_str());
        } else if (q.needed > 1) {
            std::snprintf(buf, sizeof(buf), "     %s   %d von %d", q.task.c_str(), q.progress, q.needed);
        } else {
            std::snprintf(buf, sizeof(buf), "     %s", q.task.c_str());
        }
        out.push_back(buf);

        std::snprintf(buf, sizeof(buf), "     Lohn %d Gold, %d XP", q.gold, q.xp);
        out.push_back(buf);
        out.push_back("");
        if (shown >= 5) break;
    }
    if (shown == 0) {
        out.push_back("  Noch nichts angenommen.");
        out.push_back("  Bewohner mit ! geben Auftraege.");
        out.push_back("");
    }

    out.push_back("#WARTET AUF DICH");
    int avail = 0;
    for (const Quest& q : quests) {
        if (q.state != QUEST_OFFERED) continue;
        std::snprintf(buf, sizeof(buf), "  %s", q.title.c_str());
        out.push_back(buf);
        std::snprintf(buf, sizeof(buf), "     bei %s in %s", q.giver.c_str(), q.place.c_str());
        out.push_back(buf);
        if (++avail >= 4) break;
    }
    if (avail == 0) out.push_back("  Finde weitere Doerfer.");

    out.push_back("");
    std::snprintf(buf, sizeof(buf), "#ERLEDIGT   %d", completed);
    out.push_back(buf);
    return out;
}

}
