package io.github.geeorge4.jarvis;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class Commands {
    private static final Pattern TIMER = Pattern.compile(
        "(?:поставь\\s+)?таймер(?:\\s+на)?\\s+(\\d{1,5})\\s*(с|сек(?:унд[уы]?)?|м|мин(?:ут[уы]?)?)");

    static String normalize(String text) {
        return text.trim().toLowerCase(Locale.ROOT).replace('ё', 'е').replaceAll("[.!?]+$", "").trim();
    }

    // Zero means no timer command; a negative value means an invalid duration.
    static int timerSeconds(String text) {
        Matcher match = TIMER.matcher(text);
        if (!match.matches()) return text.startsWith("таймер") || text.startsWith("поставь таймер") ? -1 : 0;
        int seconds = Integer.parseInt(match.group(1)) * (match.group(2).startsWith("м") ? 60 : 1);
        return seconds > 0 && seconds <= 86400 ? seconds : -1;
    }

    private Commands() {}
}

