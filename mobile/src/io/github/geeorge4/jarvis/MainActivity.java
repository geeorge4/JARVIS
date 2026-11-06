package io.github.geeorge4.jarvis;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.speech.RecognizerIntent;
import android.speech.tts.TextToSpeech;
import android.speech.tts.Voice;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONException;

public final class MainActivity extends Activity {
    private static final int BG = Color.rgb(12, 18, 28);
    private static final int PANEL = Color.rgb(25, 38, 56);
    private static final int LIGHT = Color.rgb(225, 238, 255);
    private static final int BLUE = Color.rgb(110, 198, 255);
    private static final int MUTED = Color.rgb(159, 181, 208);
    private static final Locale RU = new Locale("ru", "RU");
    private static final String HELP = "Скажи или напиши: «который час», «какая дата», «открой YouTube», «открой настройки», «заметка купить молоко», «покажи заметки» или «таймер 5 минут».";
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ArrayList<String> history = new ArrayList<>();
    private SharedPreferences prefs;
    private TextToSpeech speech;
    private boolean voiceReady;
    private ScrollView scroll;
    private LinearLayout messages;
    private TextView status;
    private EditText input;
    private long deadline;
    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (deadline == 0) return;
            long remaining = (deadline - SystemClock.elapsedRealtime() + 999) / 1000;
            if (remaining <= 0) {
                deadline = 0;
                status.setText("Локальный помощник");
                reply("Время вышло.");
            } else {
                status.setText(String.format(RU, "Таймер · %02d:%02d", remaining / 60, remaining % 60));
                handler.postDelayed(this, 250);
            }
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("jarvis", MODE_PRIVATE);
        if (android.os.Build.VERSION.SDK_INT >= 30) getWindow().setDecorFitsSystemWindows(false);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        LinearLayout page = column();
        page.setBackgroundColor(BG);
        page.setOnApplyWindowInsetsListener((view, insets) -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets space = insets.getInsets(WindowInsets.Type.systemBars()
                    | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
                view.setPadding(dp(16) + space.left, dp(12) + space.top,
                    dp(16) + space.right, dp(12) + space.bottom);
            }
            return insets;
        });
        page.setPadding(dp(16), dp(12), dp(16), dp(12));

        TextView heading = label("J A R V I S", 28, BLUE);
        heading.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        page.addView(heading);
        status = label("Локальный помощник", 13, MUTED);
        page.addView(status);

        LinearLayout shortcuts = new LinearLayout(this);
        shortcuts.addView(button("Команды", () -> reply(HELP)), weighted());
        shortcuts.addView(button("Заметки", () -> submit("покажи заметки")), weighted());
        page.addView(shortcuts);

        scroll = new ScrollView(this);
        messages = column();
        scroll.addView(messages);
        page.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        Switch voice = new Switch(this);
        voice.setText("Озвучивать ответы");
        voice.setTextColor(MUTED);
        voice.setChecked(prefs.getBoolean("speak", false));
        voice.setOnCheckedChangeListener((view, checked) -> {
            prefs.edit().putBoolean("speak", checked).apply();
            if (!checked && speech != null) speech.stop();
            if (checked) reply(voiceReady ? "Озвучка включена." : "Установи русский голос без сети в настройках синтеза речи Android.");
        });
        page.addView(voice);

        LinearLayout composer = new LinearLayout(this);
        composer.setGravity(Gravity.CENTER_VERTICAL);
        input = new EditText(this);
        input.setSingleLine(true);
        input.setHint("Команда…");
        input.setTextColor(LIGHT);
        input.setHintTextColor(MUTED);
        input.setImeOptions(EditorInfo.IME_ACTION_SEND);
        input.setOnEditorActionListener((view, action, event) -> {
            if (action != EditorInfo.IME_ACTION_SEND) return false;
            submitInput();
            return true;
        });
        composer.addView(input, weighted());
        composer.addView(button("Голос", this::listen));
        composer.addView(button("ОК", this::submitInput));
        page.addView(composer);
        setContentView(page);

        if (state != null) {
            ArrayList<String> previous = state.getStringArrayList("history");
            if (previous != null) for (String line : previous) addLine(line);
            deadline = state.getLong("deadline");
            tick.run();
        }
        if (history.isEmpty()) addLine("JARVIS · Готов. Нажми «Команды», чтобы увидеть примеры.");
        speech = new TextToSpeech(this, result -> handler.post(() -> {
            if (isDestroyed() || speech == null || result != TextToSpeech.SUCCESS) return;
            Set<Voice> voices = speech.getVoices();
            if (voices == null) return;
            for (Voice candidate : voices) {
                if ("ru".equals(candidate.getLocale().getLanguage()) && !candidate.isNetworkConnectionRequired()) {
                    voiceReady = speech.setVoice(candidate) == TextToSpeech.SUCCESS;
                    if (voiceReady) break;
                }
            }
        }));
    }

    private void submitInput() {
        String text = input.getText().toString().trim();
        if (!text.isEmpty()) {
            input.setText("");
            submit(text);
        }
    }

    private void submit(String text) {
        text = text.trim();
        if (text.isEmpty()) return;
        if (text.length() > 1000) { reply("Команда слишком длинная. Максимум 1000 символов."); return; }
        addLine("Ты · " + text);
        String body = text.replaceFirst("(?iu)^джарвис(?:,\\s*|\\s+)", "");
        String command = Commands.normalize(body);
        switch (command) {
            case "помощь": case "команды": reply(HELP); return;
            case "который час": case "время": reply(format("HH:mm")); return;
            case "какая дата": case "дата": reply(format("d MMMM yyyy")); return;
            case "открой youtube": case "открой ютуб":
                open(new Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com/")), "Открываю YouTube."); return;
            case "открой настройки":
                open(new Intent(android.provider.Settings.ACTION_SETTINGS), "Открываю настройки Android."); return;
            case "покажи заметки": case "заметки": showNotes(); return;
            case "останови таймер": case "отмени таймер":
                deadline = 0;
                handler.removeCallbacks(tick);
                status.setText("Локальный помощник");
                reply("Таймер остановлен."); return;
            default: break;
        }
        if (command.startsWith("заметка ")) {
            JSONArray notes = readNotes();
            if (notes.length() >= 100) { reply("В заметках уже 100 записей."); return; }
            notes.put(body.substring("заметка ".length()).trim());
            prefs.edit().putString("notes", notes.toString()).apply();
            reply("Заметка сохранена.");
            return;
        }
        int seconds = Commands.timerSeconds(command);
        if (seconds > 0) {
            handler.removeCallbacks(tick);
            deadline = SystemClock.elapsedRealtime() + seconds * 1000L;
            tick.run();
            reply("Таймер запущен на " + seconds + " сек.");
        } else if (seconds < 0) reply("Пример: «таймер 30 секунд» или «таймер 5 минут».");
        else reply("Этой команды пока нет. Нажми «Команды», чтобы посмотреть доступные.");
    }

    private JSONArray readNotes() {
        try { return new JSONArray(prefs.getString("notes", "[]")); }
        catch (JSONException error) { return new JSONArray(); }
    }

    private void showNotes() {
        JSONArray notes = readNotes();
        String[] lines = new String[notes.length()];
        for (int i = 0; i < lines.length; i++) lines[i] = notes.optString(i);
        if (lines.length == 0) { reply("Заметок пока нет. Напиши «заметка» и текст."); return; }
        new AlertDialog.Builder(this).setTitle("Заметки")
            .setItems(lines, (dialog, index) -> new AlertDialog.Builder(this)
                .setTitle("Заметка").setMessage(lines[index])
                .setPositiveButton("Закрыть", null)
                .setNeutralButton("Удалить", (removeDialog, button) -> {
                    notes.remove(index);
                    prefs.edit().putString("notes", notes.toString()).apply();
                    reply("Заметка удалена.");
                }).show())
            .setPositiveButton("Закрыть", null).show();
    }

    private void listen() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            .putExtra(RecognizerIntent.EXTRA_PROMPT, "Скажи команду JARVIS");
        try { startActivityForResult(intent, 1); }
        catch (ActivityNotFoundException error) { reply("На устройстве нет службы голосового ввода. Введи команду текстом."); }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != 1 || result != RESULT_OK || data == null) return;
        ArrayList<String> phrases = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
        if (phrases != null && !phrases.isEmpty()) {
            input.setText(phrases.get(0));
            input.setSelection(input.length());
        }
    }

    private void open(Intent intent, String message) {
        try { startActivity(intent); reply(message); }
        catch (ActivityNotFoundException error) { reply("На устройстве нет приложения для этой команды."); }
    }

    private void reply(String text) {
        addLine("JARVIS · " + text);
        if (voiceReady && prefs.getBoolean("speak", false))
            speech.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis");
    }

    private void addLine(String line) {
        if (history.size() == 40) { history.remove(0); messages.removeViewAt(0); }
        history.add(line);
        TextView bubble = label(line, 16, LIGHT);
        GradientDrawable background = new GradientDrawable();
        background.setColor(PANEL);
        background.setCornerRadius(dp(14));
        bubble.setBackground(background);
        bubble.setPadding(dp(12), dp(10), dp(12), dp(10));
        bubble.setTextIsSelectable(true);
        LinearLayout.LayoutParams bounds = new LinearLayout.LayoutParams(-1, -2);
        bounds.bottomMargin = dp(8);
        messages.addView(bubble, bounds);
        scroll.post(() -> scroll.fullScroll(View.FOCUS_DOWN));
    }

    private String format(String pattern) { return new SimpleDateFormat(pattern, RU).format(new Date()); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private LinearLayout column() { LinearLayout layout = new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL); return layout; }
    private LinearLayout.LayoutParams weighted() { return new LinearLayout.LayoutParams(0, -2, 1); }
    private TextView label(String text, int size, int color) {
        TextView view = new TextView(this);
        view.setText(text); view.setTextSize(size); view.setTextColor(color);
        return view;
    }
    private Button button(String title, Runnable action) {
        Button button = new Button(this);
        button.setText(title); button.setTextColor(BLUE); button.setAllCaps(false);
        button.setMinWidth(0); button.setMinimumWidth(0);
        button.setOnClickListener(view -> action.run());
        return button;
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putStringArrayList("history", history);
        state.putLong("deadline", deadline);
    }

    @Override protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (speech != null) speech.shutdown();
        super.onDestroy();
    }
}

