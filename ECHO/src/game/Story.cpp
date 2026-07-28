#include "Story.h"

namespace echo {

namespace {

const ItemDef kItems[ITEM_COUNT] = {
    { "Taschenlampe", "Sie flackert. Der Kontakt ist locker.", false, false },
    { "Batterie", "Halb entladen. Besser als nichts.", true, false },
    { "Stationsschluessel", "Messing. Abgegriffen. Station B.", false, true },
    { "Kellerschluessel", "Schwer. Rostig. Riecht nach Chlor.", false, true },
    { "OP-Schluessel", "Steril verpackt gewesen. Die Folie fehlt.", false, true },
    { "Archivschluessel", "Ein Zettel klebt daran: NICHT OEFFNEN.", false, true },
    { "Zugangskarte", "Name unleserlich. Das Foto zeigt niemanden.", false, true },
    { "Kassettenrekorder", "Spult von selbst zurueck.", false, false },
    { "Feuerzeug", "Fast leer. Reicht fuer wenige Sekunden.", false, false },
    { "Bolzenschneider", "Jemand hat ihn bereits benutzt.", false, false },
    { "Sicherung", "10 Ampere. Der Sockel ist verschmort.", true, false },
    { "Foto", "Ein Zimmer. Ein Bett. Kein Patient.", false, false },
    { "Patientenarmband", "Der Name darauf ist Ihrer.", false, false }
};

const Ending kEndings[ENDING_COUNT] = {
    {
        "release",
        "AUSGANG",
        "Ruhig gespielt, Dokumente gelesen, Wahrheit akzeptiert",
        {
            "Die Tuer am Ende des Ostflurs war die ganze Zeit offen.",
            "Sie brauchten nur lange genug stehen zu bleiben, um es zu bemerken.",
            "Draussen ist es weder Tag noch Nacht. Es ist einfach draussen.",
            "Hinter Ihnen erlischt Licht fuer Licht, ohne Eile.",
            "Das Gebaeude hat aufgehoert, Sie zu brauchen.",
            "Sie erinnern sich nicht an Ihren Namen. Es stoert Sie nicht mehr."
        }
    },
    {
        "denial",
        "VERWEIGERUNG",
        "Dokumente ignoriert, viel gerannt, selten stehen geblieben",
        {
            "Sie finden den Ausgang. Natuerlich finden Sie ihn.",
            "Der Parkplatz ist leer. Ihr Wagen steht dort, wo Sie ihn nie abgestellt haben.",
            "Im Rueckspiegel ist das Krankenhaus dunkel und geschlossen und voellig normal.",
            "Sie fahren nach Hause. Sie schlafen. Sie stehen auf.",
            "Am Morgen riecht Ihre Wohnung nach Desinfektionsmittel.",
            "Sie beschliessen, nicht darueber nachzudenken."
        }
    },
    {
        "loop",
        "KREIS",
        "Immer dieselben Raeume benutzt, kaum erkundet",
        {
            "Der Flur endet dort, wo er begonnen hat.",
            "Dasselbe Bett. Dieselbe Decke, halb heruntergezogen.",
            "Der Kittel auf dem Stuhl ist noch warm.",
            "Sie wachen auf. Es ist der erste Tag.",
            "Sie waren noch nie hier.",
            "Sie waren immer hier."
        }
    },
    {
        "dissolution",
        "AUFLOESUNG",
        "Lange im Dunkeln geblieben, hohe Anspannung, tiefe Etagen",
        {
            "Im Keller hoert das Gebaeude auf, sich anzustrengen.",
            "Die Waende geben ihre Form auf, weil niemand mehr hinsieht.",
            "Was von Ihnen uebrig ist, passt in ein Zimmer ohne Nummer.",
            "Es ist nicht kalt. Es ist nichts.",
            "Irgendwo oben geht ein Licht an, fuer einen neuen Besucher.",
            "Sie sind jetzt Teil der Beleuchtung."
        }
    },
    {
        "witness",
        "ZEUGE",
        "Alle Ebenen der Wahrheit gefunden, Gestalten nicht gemieden",
        {
            "Sie stehen still, als die Gestalt den Flur betritt.",
            "Sie rennen nicht. Sie sehen hin.",
            "Es ist eine Frau in einem Kittel, muede, ganz gewoehnlich.",
            "Sie sieht Sie an, als haette sie lange gewartet.",
            "Danke, sagt sie, ohne den Mund zu bewegen. Jemand musste es sehen.",
            "Das Licht geht aus. Diesmal bleibt es aus, und das ist in Ordnung."
        }
    }
};

void addDoc(std::vector<Document>& v, int id, const char* title, const char* author, const char* date, int layer,
            std::initializer_list<const char*> pages) {
    Document d;
    d.id = id;
    d.title = title;
    d.author = author;
    d.date = date;
    d.truthLayer = layer;
    for (const char* p : pages) d.pages.push_back(p);
    v.push_back(d);
}

void addLog(std::vector<AudioLog>& v, int id, const char* title, const char* speaker, int layer,
            std::initializer_list<const char*> lines) {
    AudioLog l;
    l.id = id;
    l.title = title;
    l.speaker = speaker;
    l.truthLayer = layer;
    for (const char* s : lines) {
        l.lines.push_back(s);
        l.lineDurations.push_back(1.6f + (float)std::strlen(s) * 0.052f);
    }
    v.push_back(l);
}

}

const ItemDef& itemDef(int id) {
    static ItemDef unknown = { "Unbekannt", "", false, false };
    if (id < 0 || id >= ITEM_COUNT) return unknown;
    return kItems[id];
}

const Ending& StoryDatabase::ending(int id) {
    if (id < 0 || id >= ENDING_COUNT) return kEndings[0];
    return kEndings[id];
}

const Document* StoryDatabase::document(int id) const {
    for (const auto& d : docs) if (d.id == id) return &d;
    return nullptr;
}

const AudioLog* StoryDatabase::audioLog(int id) const {
    for (const auto& l : logs) if (l.id == id) return &l;
    return nullptr;
}

void StoryDatabase::build() {
    docs.clear();
    logs.clear();

    addDoc(docs, 0, "Aufnahmebogen", "Notaufnahme", "14.03.", 0, {
        "Patient wurde um 03:12 eingeliefert. Keine Begleitung.\nKeine Papiere. Keine Verletzungen.",
        "Auf die Frage nach dem Namen antwortete der Patient\nmit dem Namen dieses Krankenhauses.",
        "Zur Beobachtung auf Station B verlegt.\nZimmer 214."
    });

    addDoc(docs, 1, "Dienstplan", "Verwaltung", "11.03.", 0, {
        "Nachtdienst Station B: Bergmann, Kastner, Ochs.",
        "Handschriftlicher Nachtrag:\nOchs erscheint seit dem 6. nicht mehr.\nBitte streichen.",
        "Zweiter Nachtrag, andere Handschrift:\nOchs war gestern hier. Er sagt, er habe\nnie gefehlt. Bitte nicht streichen."
    });

    addDoc(docs, 2, "Wartungsprotokoll", "Technik", "02.03.", 0, {
        "Ostflur, Leuchten 12 bis 19: ausgetauscht.",
        "Ostflur, Leuchten 12 bis 19: erneut defekt.\nSelber Tag.",
        "Anmerkung: Der Flur ist laut Plan 40 Meter lang.\nGemessen: 61 Meter. Messung wiederholt.\nGemessen: 44 Meter. Ich hoere auf zu messen."
    });

    addDoc(docs, 3, "Verlegungsliste", "Station B", "17.03.", 1, {
        "Alle Patienten wurden am 16.03. verlegt.\nZielklinik: siehe Anlage.",
        "Die Anlage fehlt.",
        "Handschrift am Rand:\nEs gab keine Anlage. Es gab keine Zielklinik.\nEs gab am 16. auch keine Busse."
    });

    addDoc(docs, 4, "Befund Radiologie", "Dr. Kastner", "19.03.", 1, {
        "Aufnahme Thorax. Patient 214.",
        "Auf dem Bild ist ein Flur zu sehen.\nDas Geraet wurde geprueft. Es ist in Ordnung.",
        "Zweite Aufnahme: derselbe Flur, naeher.\nWir haben das Geraet abgeschaltet."
    });

    addDoc(docs, 5, "Brief", "Bergmann", "21.03.", 1, {
        "Liebe Anna,\nich schreibe das im Schwesternzimmer,\nweil ich nicht nach Hause gehen kann.",
        "Der Weg nach draussen ist nicht weg.\nEr ist nur nicht mehr wichtig.\nDas Haus entscheidet, was wichtig ist.",
        "Wenn du das liest, geh nicht in den Keller,\nweil du dich fragst, ob es stimmt.\nDas Fragen ist der Weg hinunter."
    });

    addDoc(docs, 6, "Gutachten", "Externe Pruefstelle", "04.04.", 2, {
        "Das Objekt wurde 1998 geschlossen.",
        "Die Schliessung erfolgte, nachdem ueber vier Wochen\nkein Personal mehr das Gebaeude verlassen hatte.",
        "Die Ermittlung ergab: es hat nie Personal gegeben.\nDie Gehaltslisten sind leer.\nDie Dienstplaene sind ausgefuellt."
    });

    addDoc(docs, 7, "Notiz an mich selbst", "unbekannt", "-", 2, {
        "Wenn du das hier zum zweiten Mal liest,\nhast du den Ostflur schon dreimal genommen.",
        "Der Trick ist nicht, den Ausgang zu finden.\nDer Trick ist, ihn nicht zu suchen.",
        "Bleib stehen. Sieh hin. Warte, bis das Haus\nsich langweilt."
    });

    addDoc(docs, 8, "Patientenakte 214", "Station B", "-", 2, {
        "Name: (Feld leer)\nAufnahme: (Feld leer)\nEntlassung: (Feld leer)",
        "Diagnose: Der Patient glaubt, ein Besucher zu sein.",
        "Therapie: keine.\nProgose: das Haus ist geduldig."
    });

    addLog(logs, 0, "Bandaufnahme 1", "Schwester Bergmann", 0, {
        "Zweiter Nachtdienst diese Woche.",
        "Der Ostflur hat wieder kein Licht.",
        "Ich habe zwei Mal die gleiche Tuer geoeffnet.",
        "Wahrscheinlich bin ich einfach muede."
    });

    addLog(logs, 1, "Bandaufnahme 2", "Dr. Kastner", 0, {
        "Ich spreche das auf, weil ich es sonst aufschreibe,",
        "und aufgeschriebenes verschwindet hier.",
        "Zimmer 214 ist seit Tagen leer.",
        "Das Bett ist jeden Morgen benutzt."
    });

    addLog(logs, 2, "Bandaufnahme 3", "Hausmeister Ochs", 1, {
        "Der Keller ist groesser als der Grundriss.",
        "Ich habe es nachgemessen, mit Schnur.",
        "Die Schnur war zu kurz. Zwei Mal.",
        "Beim dritten Mal war sie zu lang.",
        "Ich gehe da nicht mehr runter."
    });

    addLog(logs, 3, "Bandaufnahme 4", "Schwester Bergmann", 1, {
        "Heute stand jemand am Ende des Flurs.",
        "Ich habe nicht weggesehen.",
        "Das war wichtig. Ich weiss nicht warum.",
        "Wer wegsieht, geht verloren.",
        "Wer hinsieht, wird gesehen."
    });

    addLog(logs, 4, "Bandaufnahme 5", "unbekannt", 2, {
        "Sie sind nicht der Erste, der das hoert.",
        "Sie sind nicht der Erste, der glaubt, er sei wach.",
        "Das Haus faellt Ihnen nicht auf, weil es sich langsam bewegt.",
        "So wie ein Zeiger. So wie eine Tuer.",
        "Bleiben Sie ruhig. Es misst Sie."
    });

    addLog(logs, 5, "Bandaufnahme 6", "Sie selbst", 2, {
        "Ich nehme das auf, damit ich es spaeter glaube.",
        "Ich bin nicht als Besucher hier hereingekommen.",
        "Auf meinem Handgelenk ist ein Band.",
        "Auf dem Band steht mein Name.",
        "Ich kann ihn nicht lesen."
    });
}

}
