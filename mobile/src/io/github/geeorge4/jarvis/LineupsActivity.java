package io.github.geeorge4.jarvis;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.widget.*;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Locale;
import java.util.Random;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public final class LineupsActivity extends Activity {
    private final ArrayList<JSONObject> cards = new ArrayList<>();
    private final ArrayList<JSONObject> matches = new ArrayList<>();
    private ArrayAdapter<String> rows;
    private final Uri[] photos = new Uri[2];
    private SharedPreferences prefs;
    private LinearLayout page;
    private EditText search, map, title, method;
    private ListView list;
    private Button favorites;
    private boolean onlyFavorites;
    private JSONObject previous;
    private int editing = -2;
    private boolean ready;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("dust2_lineups", MODE_PRIVATE);
        try {
            JSONArray saved = new JSONArray(prefs.getString("cards", "[]"));
            for (int i = 0; i < saved.length(); i++) cards.add(saved.getJSONObject(i));
            ready = true;
        } catch (JSONException error) {
            new AlertDialog.Builder(this).setMessage("Не удалось прочитать библиотеку.")
                .setPositiveButton("Закрыть", (d, w) -> finish()).setCancelable(false).show();
            return;
        }
        if (state != null && state.getInt("editing", -2) != -2) {
            for (int i = 0; i < 2; i++) {
                String uri = state.getString("photo" + i);
                photos[i] = uri == null ? null : Uri.parse(uri);
            }
            editor(state.getInt("editing"), state.getString("map"), state.getString("title"), state.getString("method"));
        } else library(state == null ? getIntent().getStringExtra("query") : state.getString("query"));
    }

    private void screen() {
        page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int padding = dp(16);
        page.setPadding(padding, padding, padding, padding);
        if (android.os.Build.VERSION.SDK_INT >= 30) page.setOnApplyWindowInsetsListener((view, insets) -> {
            android.graphics.Insets space = insets.getInsets(android.view.WindowInsets.Type.systemBars()
                | android.view.WindowInsets.Type.displayCutout() | android.view.WindowInsets.Type.ime());
            view.setPadding(padding + space.left, padding + space.top, padding + space.right, padding + space.bottom);
            return insets;
        });
        setContentView(page);
    }

    private int dp(int size) { return Math.round(size * getResources().getDisplayMetrics().density); }

    private Button button(LinearLayout parent, String name, Runnable action) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(name);
        button.setOnClickListener(v -> action.run());
        parent.addView(button);
        return button;
    }

    private EditText field(LinearLayout parent, String hint, String value) {
        EditText field = new EditText(this);
        field.setHint(hint);
        field.setText(value);
        parent.addView(field, new LinearLayout.LayoutParams(-1, -2));
        return field;
    }

    private void library(String query) {
        editing = -2;
        screen();
        TextView heading = new TextView(this);
        heading.setText("Тренер раскидок");
        heading.setTextSize(26);
        page.addView(heading);
        search = field(page, "Поиск по карте, названию и броску", query);
        search.setSingleLine(true);
        LinearLayout actions = new LinearLayout(this);
        page.addView(actions);
        button(actions, "Добавить", () -> {
            photos[0] = photos[1] = null;
            editor(-1, "", "", "");
        });
        favorites = button(actions, "Все", () -> { onlyFavorites = !onlyFavorites; refresh(); });
        button(actions, "Тренировка", this::practice);
        list = new ListView(this);
        rows = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1);
        list.setAdapter(rows);
        page.addView(list, new LinearLayout.LayoutParams(-1, 0, 1));
        TextView empty = new TextView(this);
        empty.setText("Здесь появятся найденные раскидки.");
        page.addView(empty);
        list.setEmptyView(empty);
        list.setOnItemClickListener((parent, view, position, id) -> showCard(matches.get(position)));
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) { refresh(); }
            public void afterTextChanged(Editable text) {}
        });
        refresh();
    }

    private void refresh() {
        matches.clear();
        ArrayList<String> labels = new ArrayList<>();
        String[] terms = search.getText().toString().toLowerCase(Locale.ROOT).trim().split("\\s+");
        for (JSONObject card : cards) {
            if (onlyFavorites && !card.optBoolean("favorite")) continue;
            String text = (name(card) + " " + card.optString("method")).toLowerCase(Locale.ROOT);
            boolean match = true;
            for (String term : terms) if (!text.contains(term)) { match = false; break; }
            if (match) {
                matches.add(card);
                labels.add((card.optBoolean("favorite") ? "★ " : "") + name(card));
            }
        }
        rows.clear();
        rows.addAll(labels);
        favorites.setText(onlyFavorites ? "★ Избранные" : "Все");
    }

    private String name(JSONObject card) { return card.optString("map") + " · " + card.optString("title"); }

    private void practice() {
        if (matches.isEmpty()) {
            Toast.makeText(this, "В текущей подборке пока нет раскидок.", Toast.LENGTH_SHORT).show();
            return;
        }
        ArrayList<JSONObject> pool = new ArrayList<>(matches);
        if (pool.size() > 1) pool.remove(previous);
        JSONObject card = pool.get(new Random().nextInt(pool.size()));
        previous = card;
        new AlertDialog.Builder(this).setTitle(name(card))
            .setMessage("Вспомни позицию, ориентир и способ броска.")
            .setPositiveButton("Показать", (d, w) -> showCard(card)).setNegativeButton("Закрыть", null).show();
    }

    private void showCard(JSONObject card) {
        ScrollView scroll = new ScrollView(this);
        LinearLayout details = new LinearLayout(this);
        details.setOrientation(LinearLayout.VERTICAL);
        int inset = dp(16);
        details.setPadding(inset, inset, inset, inset);
        scroll.addView(details);
        TextView explanation = new TextView(this);
        explanation.setText(card.optString("method"));
        details.addView(explanation);
        picture(details, card.optString("aim"), "Прицел");
        picture(details, card.optString("landing"), "Приземление");
        button(details, card.optBoolean("favorite") ? "Убрать из избранного" : "В избранное", () -> {
            try { card.put("favorite", !card.optBoolean("favorite")); persist(); refresh(); ((Button) details.getChildAt(details.getChildCount() - 1)).setText(
                card.optBoolean("favorite") ? "Убрать из избранного" : "В избранное"); }
            catch (JSONException error) { throw new IllegalStateException(error); }
        });
        new AlertDialog.Builder(this).setTitle(name(card)).setView(scroll)
            .setNegativeButton("Закрыть", null)
            .setNeutralButton("Удалить", (d, w) -> new AlertDialog.Builder(this)
                .setMessage("Удалить «" + name(card) + "»?")
                .setPositiveButton("Удалить", (confirm, choice) -> { cards.remove(card); persist(); refresh(); })
                .setNegativeButton("Отмена", null).show())
            .setPositiveButton("Править", (d, w) -> {
                photos[0] = photoUri(card.optString("aim"));
                photos[1] = photoUri(card.optString("landing"));
                editor(cards.indexOf(card), card.optString("map"), card.optString("title"), card.optString("method"));
            }).show();
    }

    private static Uri photoUri(String text) { return text.isEmpty() ? null : Uri.parse(text); }

    private void picture(LinearLayout details, String uri, String caption) {
        if (uri.isEmpty()) return;
        TextView label = new TextView(this);
        label.setText(caption);
        details.addView(label);
        try {
            BitmapFactory.Options options = new BitmapFactory.Options();
            options.inJustDecodeBounds = true;
            Uri source = Uri.parse(uri);
            try (InputStream in = getContentResolver().openInputStream(source)) {
                BitmapFactory.decodeStream(in, null, options);
            }
            options.inJustDecodeBounds = false;
            options.inSampleSize = 1;
            while (Math.max(options.outWidth, options.outHeight) / options.inSampleSize > 2048) options.inSampleSize *= 2;
            try (InputStream in = getContentResolver().openInputStream(source)) {
                Bitmap image = BitmapFactory.decodeStream(in, null, options);
                if (image == null) throw new IOException();
                ImageView preview = new ImageView(this);
                preview.setAdjustViewBounds(true);
                preview.setImageBitmap(image);
                details.addView(preview, new LinearLayout.LayoutParams(-1, -2));
            }
        } catch (IOException | SecurityException error) { label.setText(caption + " · файл недоступен"); }
    }

    private void editor(int index, String mapName, String caption, String instructions) {
        editing = index;
        screen();
        ScrollView scroll = new ScrollView(this);
        page.addView(scroll);
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        scroll.addView(form);
        map = field(form, "Карта, например Inferno", mapName);
        title = field(form, "Название, например Банан → за ящики", caption);
        method = field(form, "Ориентир и способ броска", instructions);
        button(form, photos[0] == null ? "Добавить фото прицела" : "Заменить фото прицела", () -> pick(0));
        button(form, photos[1] == null ? "Добавить фото приземления" : "Заменить фото приземления", () -> pick(1));
        button(form, "Сохранить", this::save);
        button(form, "Отмена", () -> library(""));
    }

    private void pick(int slot) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*").addCategory(Intent.CATEGORY_OPENABLE);
        try { startActivityForResult(intent, 100 + slot); }
        catch (android.content.ActivityNotFoundException error) {
            Toast.makeText(this, "Выбор файлов недоступен.", Toast.LENGTH_SHORT).show();
        }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (!ready || editing == -2 || (request != 100 && request != 101) || result != RESULT_OK
                || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        try { getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION); }
        catch (SecurityException error) {
            Toast.makeText(this, "Не удалось сохранить доступ к фото.", Toast.LENGTH_SHORT).show();
            return;
        }
        photos[request - 100] = uri;
        editor(editing, value(map), value(title), value(method));
    }

    private static String value(EditText field) { return field.getText().toString().trim(); }

    private void save() {
        if (value(map).isEmpty() || value(title).isEmpty() || value(method).isEmpty()) {
            Toast.makeText(this, "Заполни карту, название и описание броска.", Toast.LENGTH_SHORT).show();
            return;
        }
        try {
            JSONObject card = new JSONObject().put("map", value(map)).put("title", value(title))
                .put("method", value(method)).put("aim", photos[0] == null ? "" : photos[0].toString())
                .put("landing", photos[1] == null ? "" : photos[1].toString());
            if (editing < 0) cards.add(card);
            else {
                card.put("favorite", cards.get(editing).optBoolean("favorite"));
                cards.set(editing, card);
            }
            persist();
            onlyFavorites = false;
            library(value(title));
        } catch (JSONException error) { throw new IllegalStateException(error); }
    }

    private void persist() {
        JSONArray data = new JSONArray();
        for (JSONObject card : cards) data.put(card);
        prefs.edit().putString("cards", data.toString()).apply();
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putInt("editing", editing);
        if (editing != -2) {
            state.putString("map", value(map));
            state.putString("title", value(title));
            state.putString("method", value(method));
            for (int i = 0; i < 2; i++) if (photos[i] != null) state.putString("photo" + i, photos[i].toString());
        } else if (search != null) state.putString("query", value(search));
    }

}
