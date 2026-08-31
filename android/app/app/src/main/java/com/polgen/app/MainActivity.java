package com.polgen.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.PowerManager;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

/**
 * PolGen — автономное приложение (python-ядро RVC внутри APK, без Termux).
 *
 * Сценарий запуска:
 *  1. стартует Python (Chaquopy) и фоновый поток с bootstrap.main();
 *  2. bootstrap докачивает модели при первом запуске и поднимает
 *     веб-сервер PolGen на 127.0.0.1:4000;
 *  3. как только порт отвечает — показываем WebView с интерфейсом.
 *
 * Прогресс передаётся из Python вызовом onStatus(String) — Chaquopy
 * позволяет питону вызывать методы переданного ему Java-объекта.
 */
public class MainActivity extends Activity {

    private static final String URL = "http://127.0.0.1:4000";

    private WebView webView;
    private LinearLayout splash;
    private TextView statusText;
    private ProgressBar progress;
    private PowerManager.WakeLock wakeLock;
    private volatile boolean webShown = false;

    /** Вызывается из Python (поток сервера): статус/прогресс инициализации. */
    public void onStatus(final String message) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (statusText != null) {
                    statusText.setText(message);
                }
            }
        });
    }

    @SuppressLint({"SetJavaScriptEnabled", "WakeLockPermission"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // ── интерфейс: WebView + экран загрузки поверх него ──────────────
        webView = new WebView(this);
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        webView.setBackgroundColor(Color.parseColor("#10141A"));

        splash = new LinearLayout(this);
        splash.setOrientation(LinearLayout.VERTICAL);
        splash.setGravity(Gravity.CENTER);
        splash.setBackgroundColor(Color.parseColor("#10141A"));

        progress = new ProgressBar(this);
        progress.setIndeterminate(true);
        LinearLayout.LayoutParams pb = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        splash.addView(progress, pb);

        statusText = new TextView(this);
        statusText.setTextColor(Color.parseColor("#8899AA"));
        statusText.setGravity(Gravity.CENTER);
        statusText.setPadding(dp(24), dp(16), dp(24), 0);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        splash.addView(statusText, tp);

        TextView title = new TextView(this);
        title.setText("PolGen");
        title.setTextColor(Color.parseColor("#4CE07A"));
        title.setTextSize(26.0f);
        title.setPadding(dp(24), dp(48), dp(24), 0);
        LinearLayout.LayoutParams tt = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        splash.addView(title, 0, tt);

        FrameLayout root = new FrameLayout(this);
        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root.addView(splash, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);
        statusText.setText("Запуск Python-ядра…");

        // wake lock: конвертация не прервётся сном (пока приложение на экране)
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PolGen:run");
        wakeLock.acquire(6 * 60 * 60 * 1000L);

        // ── фоновый поток: python-сервер ─────────────────────────────────
        Thread server = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    Python py = Python.getInstance();
                    PyObject bootstrap = py.getModule("bootstrap");
                    // this передаётся в питон; bootstrap зовёт onStatus(...)
                    bootstrap.callAttr("main", getFilesDir().getAbsolutePath(), MainActivity.this);
                } catch (final Throwable t) {
                    onStatus("Ошибка запуска: " + t
                            + "\n(подробности — logcat, тег python.stdout)");
                }
            }
        });
        server.setDaemon(true);
        server.start();

        // ── ждём готовности порта, затем открываем интерфейс ─────────────
        Thread waiter = new Thread(new Runnable() {
            @Override
            public void run() {
                for (int i = 0; i < 600; i++) {   // до 5 минут (первый запуск качает модели)
                    if (portOpen()) {
                        showWeb();
                        return;
                    }
                    try {
                        Thread.sleep(500);
                    } catch (InterruptedException ignored) {
                        return;
                    }
                }
                onStatus("Сервер не поднялся за 5 минут. "
                        + "Проверь интернет (первый запуск качает модели ~560 МБ).");
            }
        });
        waiter.setDaemon(true);
        waiter.start();
    }

    private boolean portOpen() {
        try {
            java.net.Socket s = new java.net.Socket("127.0.0.1", 4000);
            s.close();
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private void showWeb() {
        if (webShown) {
            return;
        }
        webShown = true;
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                splash.setVisibility(View.GONE);
                webView.loadUrl(URL);
            }
        });
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
