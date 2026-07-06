let cachedVoice = null;
const MALE_PATTERN = /stefan|klaus|conrad|bernd|jonas|paul|markus|male|mann/i;
function pickVoice() {
    const voices = window.speechSynthesis?.getVoices() ?? [];
    if (!voices.length)
        return null;
    const german = voices.filter((v) => v.lang.toLowerCase().startsWith("de"));
    const male = german.find((v) => MALE_PATTERN.test(v.name));
    return male ?? german[0] ?? voices[0];
}
export function initTts() {
    if (!window.speechSynthesis)
        return;
    cachedVoice = pickVoice();
    window.speechSynthesis.onvoiceschanged = () => {
        cachedVoice = pickVoice();
    };
}
function cleanForSpeech(text) {
    return text
        .replace(/```[\s\S]*?```/g, " Codeblock. ")
        .replace(/\[(.*?)\]\(.*?\)/g, "$1")
        .replace(/https?:\/\/\S+/g, " Link ")
        .replace(/[*_#`>|]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}
export function speak(text) {
    return new Promise((resolve) => {
        const synth = window.speechSynthesis;
        if (!synth) {
            resolve();
            return;
        }
        synth.cancel();
        const clean = cleanForSpeech(text).slice(0, 600);
        if (!clean) {
            resolve();
            return;
        }
        if (!cachedVoice)
            cachedVoice = pickVoice();
        const utterance = new SpeechSynthesisUtterance(clean);
        if (cachedVoice)
            utterance.voice = cachedVoice;
        const male = cachedVoice ? MALE_PATTERN.test(cachedVoice.name) : false;
        utterance.lang = "de-DE";
        utterance.rate = 1.05;
        utterance.pitch = male ? 1 : 0.7;
        let settled = false;
        const finish = () => {
            if (!settled) {
                settled = true;
                resolve();
            }
        };
        utterance.onend = finish;
        utterance.onerror = finish;
        window.setTimeout(finish, 45000);
        synth.speak(utterance);
    });
}
export function stopSpeaking() {
    window.speechSynthesis?.cancel();
}
