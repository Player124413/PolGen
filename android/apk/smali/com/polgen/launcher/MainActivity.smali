.class public Lcom/polgen/launcher/MainActivity;
.super Landroid/app/Activity;
.source "MainActivity.java"

# interfaces
.implements Landroid/view/View$OnClickListener;
.implements Ljava/lang/Runnable;


# instance fields
.field private root:Landroid/widget/LinearLayout;
.field private status:Landroid/widget/TextView;
.field private logView:Landroid/widget/TextView;
.field private logScroll:Landroid/widget/ScrollView;
.field private progressBar:Landroid/widget/ProgressBar;
.field private btnInstall:Landroid/widget/Button;
.field private btnRun:Landroid/widget/Button;
.field private btnOpen:Landroid/widget/Button;
.field private btnTermux:Landroid/widget/Button;
.field private receiver:Lcom/polgen/launcher/MainActivity$ProgressReceiver;
.field private pendingScript:Ljava/lang/String;


# direct methods
.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Landroid/app/Activity;-><init>()V

    return-void
.end method


.method protected onCreate(Landroid/os/Bundle;)V
    .locals 12

    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    # корневой LinearLayout (тёмный)
    new-instance v1, Landroid/widget/LinearLayout;
    invoke-direct {v1, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V
    iput-object v1, p0, Lcom/polgen/launcher/MainActivity;->root:Landroid/widget/LinearLayout;

    const/4 v2, 0x1
    invoke-virtual {v1, v2}, Landroid/widget/LinearLayout;->setOrientation(I)V

    const v2, -0xefebe6            # 0xFF10141A
    invoke-virtual {v1, v2}, Landroid/view/View;->setBackgroundColor(I)V

    const/16 v2, 0x10
    invoke-direct {p0, v2}, Lcom/polgen/launcher/MainActivity;->dp(I)I
    move-result v3
    invoke-virtual {v1, v3, v3, v3, v3}, Landroid/view/View;->setPadding(IIII)V

    # заголовок
    const-string v4, "PolGen"
    const/high16 v5, 0x41d00000    # 26.0f
    const v6, -0xb31f86            # 0xFF4CE07A
    invoke-direct {p0, v4, v5, v6}, Lcom/polgen/launcher/MainActivity;->addText(Ljava/lang/String;FI)Landroid/widget/TextView;

    # строка статуса Termux
    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->isTermuxInstalled()Z
    move-result v8
    if-eqz v8, :no_termux
    const-string v4, "Termux: ✓ найден"
    goto :status_line
    :no_termux
    const-string v4, "Termux: не найден"
    :status_line
    const/high16 v5, 0x41500000    # 13.0f
    const v6, -0x776656            # 0xFF8899AA
    invoke-direct {p0, v4, v5, v6}, Lcom/polgen/launcher/MainActivity;->addText(Ljava/lang/String;FI)Landroid/widget/TextView;

    # строка обратной связи
    const-string v4, ""
    const/high16 v5, 0x41600000    # 14.0f
    const v6, -0x222223            # 0xFFDDDDDD
    invoke-direct {p0, v4, v5, v6}, Lcom/polgen/launcher/MainActivity;->addText(Ljava/lang/String;FI)Landroid/widget/TextView;
    move-result-object v4
    iput-object v4, p0, Lcom/polgen/launcher/MainActivity;->status:Landroid/widget/TextView;

    # кнопка Termux (если не установлен)
    if-nez v8, :btn_install

    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->hasTermuxAsset()Z
    move-result v9
    if-eqz v9, :fdroid_label
    const-string v9, "1 · Установить Termux (встроен)"
    goto :add_btn_termux
    :fdroid_label
    const-string v9, "1 · Установить Termux (F-Droid)"
    :add_btn_termux
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnTermux:Landroid/widget/Button;

    :btn_install
    const-string v9, "2 · Установить / обновить PolGen"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnInstall:Landroid/widget/Button;

    const-string v9, "▶ · Запустить PolGen"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnRun:Landroid/widget/Button;

    const-string v9, "🌐 · Открыть интерфейс"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnOpen:Landroid/widget/Button;

    const-string v9, "📋 · Скопировать команду установки"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;

    # прогресс-бар (скрыт до старта задания)
    new-instance v5, Landroid/widget/ProgressBar;
    invoke-direct {v5, p0}, Landroid/widget/ProgressBar;-><init>(Landroid/content/Context;)V
    iput-object v5, p0, Lcom/polgen/launcher/MainActivity;->progressBar:Landroid/widget/ProgressBar;
    const/4 v2, 0x1
    invoke-virtual {v5, v2}, Landroid/widget/ProgressBar;->setIndeterminate(Z)V
    const/16 v2, 0x8
    invoke-virtual {v5, v2}, Landroid/view/View;->setVisibility(I)V
    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->params()Landroid/widget/LinearLayout$LayoutParams;
    move-result-object v6
    invoke-virtual {v1, v5, v6}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    # журнал (моноширинный, занимает остаток экрана)
    new-instance v0, Landroid/widget/ScrollView;
    invoke-direct {v0, p0}, Landroid/widget/ScrollView;-><init>(Landroid/content/Context;)V
    iput-object v0, p0, Lcom/polgen/launcher/MainActivity;->logScroll:Landroid/widget/ScrollView;

    new-instance v7, Landroid/widget/TextView;
    invoke-direct {v7, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V
    iput-object v7, p0, Lcom/polgen/launcher/MainActivity;->logView:Landroid/widget/TextView;

    const/high16 v2, 0x41400000    # 12.0f
    invoke-virtual {v7, v2}, Landroid/widget/TextView;->setTextSize(F)V
    const v2, -0x665545            # 0xFF99AABB
    invoke-virtual {v7, v2}, Landroid/widget/TextView;->setTextColor(I)V
    sget-object v2, Landroid/graphics/Typeface;->MONOSPACE:Landroid/graphics/Typeface;
    invoke-virtual {v7, v2}, Landroid/widget/TextView;->setTypeface(Landroid/graphics/Typeface;)V
    const-string v2, "Журнал установки появится здесь…\n"
    invoke-virtual {v7, v2}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v0, v7}, Landroid/widget/ScrollView;->addView(Landroid/view/View;)V

    # LayoutParams(MATCH_PARENT, 0, weight=1)
    new-instance v6, Landroid/widget/LinearLayout$LayoutParams;
    const/4 v2, -0x1
    const/4 v3, 0x0
    const/high16 v4, 0x3f800000    # 1.0f
    invoke-direct {v6, v2, v3, v4}, Landroid/widget/LinearLayout$LayoutParams;-><init>(IIF)V
    invoke-virtual {v1, v0, v6}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    invoke-virtual {p0, v1}, Landroid/app/Activity;->setContentView(Landroid/view/View;)V

    # динамический ресивер прогресса (из Termux через am broadcast)
    new-instance v11, Lcom/polgen/launcher/MainActivity$ProgressReceiver;
    invoke-direct {v11, p0}, Lcom/polgen/launcher/MainActivity$ProgressReceiver;-><init>(Lcom/polgen/launcher/MainActivity;)V
    iput-object v11, p0, Lcom/polgen/launcher/MainActivity;->receiver:Lcom/polgen/launcher/MainActivity$ProgressReceiver;

    new-instance v10, Landroid/content/IntentFilter;
    const-string v2, "com.polgen.launcher.PROGRESS"
    invoke-direct {v10, v2}, Landroid/content/IntentFilter;-><init>(Ljava/lang/String;)V
    const-string v2, "com.polgen.launcher.INSTALL_STATUS"
    invoke-virtual {v10, v2}, Landroid/content/IntentFilter;->addAction(Ljava/lang/String;)V

    sget v2, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v3, 0x21             # 33
    if-lt v2, v3, :old_register
    const/4 v2, 0x2                # RECEIVER_EXPORTED
    invoke-virtual {p0, v11, v10, v2}, Landroid/content/Context;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;I)I
    move-result v2
    goto :register_done
    :old_register
    invoke-virtual {p0, v11, v10}, Landroid/content/Context;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;)I
    move-result v2
    :register_done

    return-void
.end method


.method protected onDestroy()V
    .locals 2

    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->receiver:Lcom/polgen/launcher/MainActivity$ProgressReceiver;
    if-eqz v0, :skip

    :try_start_0
    invoke-virtual {p0, v0}, Landroid/content/Context;->unregisterReceiver(Landroid/content/BroadcastReceiver;)V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    :catch_0
    :skip
    invoke-super {p0}, Landroid/app/Activity;->onDestroy()V

    return-void
.end method


# Runnable: автопрокрутка журнала вниз
.method public run()V
    .locals 2

    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->logScroll:Landroid/widget/ScrollView;
    if-eqz v0, :skip

    const/16 v1, 0x82             # View.FOCUS_DOWN
    invoke-virtual {v0, v1}, Landroid/view/View;->fullScroll(I)Z

    :skip
    return-void
.end method


# int dp(int v)
.method private dp(I)I
    .locals 2

    invoke-virtual {p0}, Landroid/app/Activity;->getResources()Landroid/content/res/Resources;
    move-result-object v0
    invoke-virtual {v0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;
    move-result-object v0
    iget v0, v0, Landroid/util/DisplayMetrics;->density:F

    int-to-float v1, p1
    mul-float/2addr v1, v0
    const/high16 v0, 0x3f000000    # 0.5f
    add-float/2addr v1, v0
    float-to-int v1, v1

    return v1
.end method


# LinearLayout.LayoutParams params()
.method private params()Landroid/widget/LinearLayout$LayoutParams;
    .locals 3

    new-instance v0, Landroid/widget/LinearLayout$LayoutParams;
    const/4 v1, -0x1             # MATCH_PARENT
    const/4 v2, -0x2             # WRAP_CONTENT
    invoke-direct {v0, v1, v2}, Landroid/widget/LinearLayout$LayoutParams;-><init>(II)V
    return-object v0
.end method


# TextView addText(String text, float sizeSp, int color)
.method private addText(Ljava/lang/String;FI)Landroid/widget/TextView;
    .locals 3

    new-instance v0, Landroid/widget/TextView;
    invoke-direct {v0, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V

    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v0, p2}, Landroid/widget/TextView;->setTextSize(F)V
    invoke-virtual {v0, p3}, Landroid/widget/TextView;->setTextColor(I)V

    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->params()Landroid/widget/LinearLayout$LayoutParams;
    move-result-object v1

    iget-object v2, p0, Lcom/polgen/launcher/MainActivity;->root:Landroid/widget/LinearLayout;
    invoke-virtual {v2, v0, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    return-object v0
.end method


# Button addButton(String text)
.method private addButton(Ljava/lang/String;)Landroid/widget/Button;
    .locals 4

    new-instance v0, Landroid/widget/Button;
    invoke-direct {v0, p0}, Landroid/widget/Button;-><init>(Landroid/content/Context;)V

    invoke-virtual {v0, p1}, Landroid/widget/Button;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v0, p0}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->params()Landroid/widget/LinearLayout$LayoutParams;
    move-result-object v1

    const/16 v2, 0x5
    invoke-direct {p0, v2}, Lcom/polgen/launcher/MainActivity;->dp(I)I
    move-result v2
    const/4 v3, 0x0
    invoke-virtual {v1, v3, v2, v3, v2}, Landroid/view/ViewGroup$MarginLayoutParams;->setMargins(IIII)V

    iget-object v2, p0, Lcom/polgen/launcher/MainActivity;->root:Landroid/widget/LinearLayout;
    invoke-virtual {v2, v0, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    return-object v0
.end method


# boolean isTermuxInstalled()
.method private isTermuxInstalled()Z
    .locals 3

    :try_start_0
    invoke-virtual {p0}, Landroid/app/Activity;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v0

    const-string v1, "com.termux"
    const/4 v2, 0x0
    invoke-virtual {v0, v1, v2}, Landroid/content/pm/PackageManager;->getPackageInfo(Ljava/lang/String;I)Landroid/content/pm/PackageInfo;

    const/4 v0, 0x1
    return v0

    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    :catch_0
    const/4 v0, 0x0
    return v0
.end method


# boolean hasTermuxAsset() — есть ли встроенный termux.apk
.method private hasTermuxAsset()Z
    .locals 3

    :try_start_0
    invoke-virtual {p0}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
    move-result-object v0
    const-string v1, "termux.apk"
    invoke-virtual {v0, v1}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v0
    invoke-virtual {v0}, Ljava/io/InputStream;->close()V

    const/4 v0, 0x1
    return v0

    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    :catch_0
    const/4 v0, 0x0
    return v0
.end method


# void setStatus(String text)
.method private setStatus(Ljava/lang/String;)V
    .locals 1

    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->status:Landroid/widget/TextView;
    if-eqz v0, :skip

    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    :skip
    return-void
.end method


# void addLog(String line) — дописать строку в журнал
.method private addLog(Ljava/lang/String;)V
    .locals 4

    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->logView:Landroid/widget/TextView;
    if-eqz v0, :skip

    invoke-virtual {v0}, Landroid/widget/TextView;->getText()Ljava/lang/CharSequence;
    move-result-object v1
    invoke-virtual {v1}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v1

    # ограничение длины журнала
    invoke-virtual {v1}, Ljava/lang/String;->length()I
    move-result v2
    const/16 v3, 0x3e80             # 16000
    if-lt v2, v3, :no_trim
    invoke-virtual {v1}, Ljava/lang/String;->length()I
    move-result v2
    const v3, 0x2ee0                 # 12000
    sub-int/2addr v2, v3
    invoke-virtual {v1, v2}, Ljava/lang/String;->substring(I)Ljava/lang/String;
    move-result-object v1
    :no_trim

    # p1 = cur + "\n" + line (если журнал не пуст)
    invoke-virtual {v1}, Ljava/lang/String;->isEmpty()Z
    move-result v2
    if-nez v2, :set_text

    new-instance v2, Ljava/lang/StringBuilder;
    invoke-static {v1}, Ljava/lang/String;->valueOf(Ljava/lang/Object;)Ljava/lang/String;
    move-result-object v3
    invoke-direct {v2, v3}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V
    const-string v3, "\n"
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v2
    invoke-virtual {v2, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v2
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object p1

    :set_text
    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    # автопрокрутка (this реализует Runnable)
    invoke-virtual {v0, p0}, Landroid/view/View;->post(Ljava/lang/Runnable;)Z

    :skip
    return-void
.end method


# void appendLog(String line) — служебные маркеры __START__/__DONE__/__FAIL__
.method public appendLog(Ljava/lang/String;)V
    .locals 3

    const-string v0, "__DONE__"
    invoke-virtual {p1, v0}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v1
    if-eqz v1, :not_done

    iget-object v2, p0, Lcom/polgen/launcher/MainActivity;->progressBar:Landroid/widget/ProgressBar;
    if-eqz v2, :done_hide
    const/16 v1, 0x8
    invoke-virtual {v2, v1}, Landroid/view/View;->setVisibility(I)V
    :done_hide
    const-string v1, "✅ Готово"
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->addLog(Ljava/lang/String;)V
    return-void

    :not_done
    const-string v0, "__FAIL__"
    invoke-virtual {p1, v0}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v1
    if-eqz v1, :not_fail

    iget-object v2, p0, Lcom/polgen/launcher/MainActivity;->progressBar:Landroid/widget/ProgressBar;
    if-eqz v2, :fail_hide
    const/16 v1, 0x8
    invoke-virtual {v2, v1}, Landroid/view/View;->setVisibility(I)V
    :fail_hide
    const-string v1, "❌ Ошибка — подробности в окне Termux"
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->addLog(Ljava/lang/String;)V
    return-void

    :not_fail
    const-string v0, "__START__"
    invoke-virtual {p1, v0}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v1
    if-eqz v1, :plain_line

    iget-object v2, p0, Lcom/polgen/launcher/MainActivity;->progressBar:Landroid/widget/ProgressBar;
    if-eqz v2, :start_logged
    const/4 v1, 0x0
    invoke-virtual {v2, v1}, Landroid/view/View;->setVisibility(I)V
    :start_logged
    const/16 v1, 0x9
    invoke-virtual {p1, v1}, Ljava/lang/String;->substring(I)Ljava/lang/String;
    move-result-object v1
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->addLog(Ljava/lang/String;)V
    return-void

    :plain_line
    invoke-direct {p0, p1}, Lcom/polgen/launcher/MainActivity;->addLog(Ljava/lang/String;)V
    return-void
.end method


# void toast(String text)
.method private toast(Ljava/lang/String;)V
    .locals 1

    const/4 v0, 0x1
    invoke-static {p0, p1, v0}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v0
    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    return-void
.end method


# void openUrl(String url)
.method private openUrl(Ljava/lang/String;)V
    .locals 3

    :try_start_0
    invoke-static {p1}, Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;
    move-result-object v0

    new-instance v1, Landroid/content/Intent;
    const-string v2, "android.intent.action.VIEW"
    invoke-direct {v1, v2, v0}, Landroid/content/Intent;-><init>(Ljava/lang/String;Landroid/net/Uri;)V

    invoke-virtual {p0, v1}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    const-string v0, "Не удалось открыть ссылку"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->toast(Ljava/lang/String;)V

    return-void
.end method


# void copyToClipboard(String text)
.method private copyToClipboard(Ljava/lang/String;)V
    .locals 2

    const-string v0, "clipboard"
    invoke-virtual {p0, v0}, Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;
    move-result-object v0
    check-cast v0, Landroid/content/ClipboardManager;

    const-string v1, "polgen"
    invoke-static {v1, p1}, Landroid/content/ClipData;->newPlainText(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Landroid/content/ClipData;
    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/content/ClipboardManager;->setClip(Landroid/content/ClipData;)V

    return-void
.end method


# void installTermux() — установка встроенного termux.apk (PackageInstaller)
.method private installTermux()V
    .locals 10

    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->hasTermuxAsset()Z
    move-result v0
    if-nez v0, :has_asset

    const-string v0, "⚠ В этой сборке нет встроенного Termux — открываю F-Droid"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->appendLog(Ljava/lang/String;)V
    const-string v0, "https://f-droid.org/packages/com.termux/"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->openUrl(Ljava/lang/String;)V
    return-void

    :has_asset
    # API 26+: проверка права устанавливать приложения
    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v1, 0x1a             # 26
    if-lt v0, v1, :do_install

    :try_start_0
    invoke-virtual {p0}, Landroid/app/Activity;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v0
    invoke-virtual {v0}, Landroid/content/pm/PackageManager;->canRequestPackageInstalls()Z
    move-result v0
    if-nez v0, :do_install
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_perm

    # нет права — открыть настройки
    :try_start_1
    new-instance v0, Landroid/content/Intent;
    const-string v1, "android.settings.MANAGE_UNKNOWN_APP_SOURCES"
    const-string v2, "package:com.polgen.launcher"
    invoke-static {v2}, Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;
    move-result-object v2
    invoke-direct {v0, v1, v2}, Landroid/content/Intent;-><init>(Ljava/lang/String;Landroid/net/Uri;)V
    invoke-virtual {p0, v0}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V
    :try_end_1
    .catch Ljava/lang/Exception; {:try_start_1 .. :try_end_1} :catch_settings

    goto :after_settings

    :catch_settings
    nop

    :after_settings
    const-string v0, "Разреши PolGen устанавливать приложения, затем нажми кнопку ещё раз"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->toast(Ljava/lang/String;)V
    return-void

    :catch_perm
    nop

    # собственно установка через PackageInstaller
    :do_install
    const/4 v0, 0x0                # InputStream in = null

    :try_start_2
    invoke-virtual {p0}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
    move-result-object v1
    const-string v2, "termux.apk"
    invoke-virtual {v1, v2}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v0

    invoke-virtual {p0}, Landroid/app/Activity;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v1
    invoke-virtual {v1}, Landroid/content/pm/PackageManager;->getPackageInstaller()Landroid/content/pm/PackageInstaller;
    move-result-object v1

    new-instance v2, Landroid/content/pm/PackageInstaller$SessionParams;
    const/4 v3, 0x1                # MODE_FULL_INSTALL
    invoke-direct {v2, v3}, Landroid/content/pm/PackageInstaller$SessionParams;-><init>(I)V
    invoke-virtual {v1, v2}, Landroid/content/pm/PackageInstaller;->createSession(Landroid/content/pm/PackageInstaller$SessionParams;)I
    move-result v2
    invoke-virtual {v1, v2}, Landroid/content/pm/PackageInstaller;->openSession(I)Landroid/content/pm/PackageInstaller$Session;
    move-result-object v2

    const-string v3, "termux.apk"
    const-wide/16 v4, 0x0
    const-wide/16 v6, -0x1
    invoke-virtual/range {v2 .. v7}, Landroid/content/pm/PackageInstaller$Session;->openWrite(Ljava/lang/String;JJ)Ljava/io/OutputStream;
    move-result-object v3

    # копирование 64 КБ кусками
    const v4, 0x10000
    new-array v4, v4, [B

    :copy_loop
    invoke-virtual {v0, v4}, Ljava/io/InputStream;->read([B)I
    move-result v5
    if-lez v5, :copy_done
    const/4 v6, 0x0
    invoke-virtual {v3, v4, v6, v5}, Ljava/io/OutputStream;->write([BII)V
    goto :copy_loop

    :copy_done
    invoke-virtual {v3}, Ljava/io/OutputStream;->flush()V
    invoke-virtual {v3}, Ljava/io/OutputStream;->close()V
    invoke-virtual {v0}, Ljava/io/InputStream;->close()V

    # commit с PendingIntent на статус
    new-instance v4, Landroid/content/Intent;
    const-string v5, "com.polgen.launcher.INSTALL_STATUS"
    invoke-direct {v4, v5}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V
    const/4 v5, 0x2
    const v6, 0xa000000               # FLAG_UPDATE_CURRENT | FLAG_MUTABLE
    invoke-static {p0, v5, v4, v6}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;
    move-result-object v4
    invoke-virtual {v4}, Landroid/app/PendingIntent;->getIntentSender()Landroid/content/IntentSender;
    move-result-object v4
    invoke-virtual {v2, v4}, Landroid/content/pm/PackageInstaller$Session;->commit(Landroid/content/IntentSender;)V

    const-string v4, "⏳ Termux: подтверди установку в появившемся системном окне…"
    invoke-direct {p0, v4}, Lcom/polgen/launcher/MainActivity;->appendLog(Ljava/lang/String;)V
    :try_end_2
    .catch Ljava/lang/Exception; {:try_start_2 .. :try_end_2} :catch_install

    return-void

    :catch_install
    move-exception v4
    invoke-virtual {v4}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v5
    const-string v6, "❌ Ошибка установки Termux: "
    invoke-virtual {v6, v5}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v5
    invoke-direct {p0, v5}, Lcom/polgen/launcher/MainActivity;->appendLog(Ljava/lang/String;)V

    :try_start_3
    if-eqz v0, :skip_close
    invoke-virtual {v0}, Ljava/io/InputStream;->close()V
    :skip_close
    :try_end_3
    .catch Ljava/lang/Exception; {:try_start_3 .. :try_end_3} :catch_close

    :catch_close
    return-void
.end method


# void handleInstallStatus(Intent) — статус PackageInstaller-сессии Termux
.method public handleInstallStatus(Landroid/content/Intent;)V
    .locals 4

    const-string v0, "android.content.pm.extra.PackageInstaller.STATUS"
    const/16 v1, -0x3e9            # -999 (нет значения)
    invoke-virtual {p1, v0, v1}, Landroid/content/Intent;->getIntExtra(Ljava/lang/String;I)I
    move-result v0

    const/4 v1, 0x1                # STATUS_PENDING_USER_ACTION
    if-ne v0, v1, :not_confirm

    const-string v1, "android.intent.extra.INTENT"
    invoke-virtual {p1, v1}, Landroid/content/Intent;->getParcelableExtra(Ljava/lang/String;)Landroid/os/Parcelable;
    move-result-object v1
    check-cast v1, Landroid/content/Intent;
    if-eqz v1, :not_confirm

    const/high16 v2, 0x10000000    # FLAG_ACTIVITY_NEW_TASK
    invoke-virtual {v1, v2}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;

    :try_start_0
    invoke-virtual {p0, v1}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_confirm

    :catch_confirm
    return-void

    :not_confirm
    if-nez v0, :not_success         # 0 = STATUS_SUCCESS

    const-string v1, "✅ Termux установлен! Открываю его для первичной настройки (~15 сек), затем вернись и жми «Установить PolGen»."
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->appendLog(Ljava/lang/String;)V

    :try_start_1
    invoke-virtual {p0}, Landroid/app/Activity;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v1
    const-string v2, "com.termux"
    invoke-virtual {v1, v2}, Landroid/content/pm/PackageManager;->getLaunchIntentForPackage(Ljava/lang/String;)Landroid/content/Intent;
    move-result-object v1
    if-eqz v1, :no_launch

    const/high16 v2, 0x10000000
    invoke-virtual {v1, v2}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    invoke-virtual {p0, v1}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V

    :no_launch
    :try_end_1
    .catch Ljava/lang/Exception; {:try_start_1 .. :try_end_1} :catch_launch

    :catch_launch
    return-void

    :not_success
    const-string v1, "android.content.pm.extra.PackageInstaller.STATUS_MESSAGE"
    invoke-virtual {p1, v1}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v1
    if-eqz v1, :no_msg

    const-string v2, "❌ Установка Termux не удалась: "
    invoke-virtual {v2, v1}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v1
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->appendLog(Ljava/lang/String;)V
    return-void

    :no_msg
    const-string v1, "❌ Установка Termux не удалась"
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->appendLog(Ljava/lang/String;)V
    return-void
.end method


# void runCommand(String script) — отправка RUN_COMMAND в Termux
.method private runCommand(Ljava/lang/String;)V
    .locals 4

    const-string v0, "com.termux.permission.RUN_COMMAND"
    invoke-virtual {p0, v0}, Landroid/content/Context;->checkSelfPermission(Ljava/lang/String;)I
    move-result v1
    if-eqz v1, :granted

    iput-object p1, p0, Lcom/polgen/launcher/MainActivity;->pendingScript:Ljava/lang/String;

    const/4 v1, 0x1
    new-array v1, v1, [Ljava/lang/String;
    const/4 v2, 0x0
    const-string v3, "com.termux.permission.RUN_COMMAND"
    aput-object v3, v1, v2

    const/4 v2, 0x1
    invoke-virtual {p0, v1, v2}, Landroid/app/Activity;->requestPermissions([Ljava/lang/String;I)V

    const-string v1, "Разреши PolGen управлять Termux, затем нажми кнопку ещё раз"
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->toast(Ljava/lang/String;)V
    return-void

    :granted
    new-instance v0, Landroid/content/Intent;
    const-string v1, "com.termux.RUN_COMMAND"
    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    new-instance v1, Landroid/content/ComponentName;
    const-string v2, "com.termux"
    const-string v3, "com.termux.app.RunCommandService"
    invoke-direct {v1, v2, v3}, Landroid/content/ComponentName;-><init>(Ljava/lang/String;Ljava/lang/String;)V
    invoke-virtual {v0, v1}, Landroid/content/Intent;->setComponent(Landroid/content/ComponentName;)Landroid/content/Intent;

    const-string v1, "/data/data/com.termux/files/usr/bin/bash"
    const-string v2, "com.termux.RUN_COMMAND_PATH"
    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;

    const/4 v1, 0x2
    new-array v1, v1, [Ljava/lang/String;
    const/4 v2, 0x0
    const-string v3, "-c"
    aput-object v3, v1, v2
    const/4 v2, 0x1
    aput-object p1, v1, v2
    const-string v2, "com.termux.RUN_COMMAND_ARGUMENTS"
    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;[Ljava/lang/String;)Landroid/content/Intent;

    const-string v1, "/data/data/com.termux/files/home"
    const-string v2, "com.termux.RUN_COMMAND_WORKDIR"
    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;

    :try_start_0
    invoke-virtual {p0, v0}, Landroid/app/Activity;->startService(Landroid/content/Intent;)Landroid/content/ComponentName;
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_fail

    const-string v1, "Команда отправлена — прогресс появится в журнале ниже."
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->setStatus(Ljava/lang/String;)V

    :try_start_1
    invoke-virtual {p0}, Landroid/app/Activity;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v1
    const-string v2, "com.termux"
    invoke-virtual {v1, v2}, Landroid/content/pm/PackageManager;->getLaunchIntentForPackage(Ljava/lang/String;)Landroid/content/Intent;
    move-result-object v1
    if-eqz v1, :no_launch

    const/high16 v2, 0x10000000    # FLAG_ACTIVITY_NEW_TASK
    invoke-virtual {v1, v2}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    invoke-virtual {p0, v1}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V

    :no_launch
    :try_end_1
    .catch Ljava/lang/Exception; {:try_start_1 .. :try_end_1} :catch_ignore

    return-void

    :catch_fail
    move-exception v1
    invoke-direct {p0, p1}, Lcom/polgen/launcher/MainActivity;->copyToClipboard(Ljava/lang/String;)V
    const-string v1, "Автозапуск не удался. Команда скопирована — открой Termux и вставь её (долгое нажатие → Вставить)."
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->setStatus(Ljava/lang/String;)V
    return-void

    :catch_ignore
    return-void
.end method


# public void onClick(View v)
.method public onClick(Landroid/view/View;)V
    .locals 3

    :try_start_0
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnTermux:Landroid/widget/Button;
    if-ne p1, v0, :not_termux

    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->installTermux()V
    return-void

    :not_termux
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnInstall:Landroid/widget/Button;
    if-ne p1, v0, :not_install

    const-string v0, "am broadcast -a com.polgen.launcher.PROGRESS --es line '__START__ Установка PolGen начата' >/dev/null 2>&1\nmkdir -p $HOME/.termux\ntouch $HOME/.termux/termux.properties\ngrep -qs 'allow-external-apps' $HOME/.termux/termux.properties || echo 'allow-external-apps = true' >> $HOME/.termux/termux.properties\ncommand -v git >/dev/null 2>&1 || { am broadcast -a com.polgen.launcher.PROGRESS --es line '⚙ git: устанавливаем' >/dev/null 2>&1; pkg install -y git; }\nif [ -d $HOME/PolGen/.git ]; then\n  am broadcast -a com.polgen.launcher.PROGRESS --es line '⬇ PolGen: обновляем' >/dev/null 2>&1\n  cd $HOME/PolGen || { am broadcast -a com.polgen.launcher.PROGRESS --es line '__FAIL__' >/dev/null 2>&1; exit 1; }\n  git pull --ff-only || { git fetch --depth 1 origin && git reset --hard FETCH_HEAD; }\nelse\n  am broadcast -a com.polgen.launcher.PROGRESS --es line '⬇ PolGen: скачиваем репозиторий' >/dev/null 2>&1\n  rm -rf $HOME/PolGen\n  git clone --depth 1 -b arena/01a057f4-polgen https://github.com/Player124413/PolGen.git $HOME/PolGen || git clone --depth 1 https://github.com/Player124413/PolGen.git $HOME/PolGen || { am broadcast -a com.polgen.launcher.PROGRESS --es line '__FAIL__' >/dev/null 2>&1; exit 1; }\n  cd $HOME/PolGen || { am broadcast -a com.polgen.launcher.PROGRESS --es line '__FAIL__' >/dev/null 2>&1; exit 1; }\nfi\nam broadcast -a com.polgen.launcher.PROGRESS --es line '⚙ Зависимости: Python, PyTorch, FFmpeg, модели — это долго' >/dev/null 2>&1\nbash android/install.sh 2>&1 | while IFS= read -r L; do am broadcast -a com.polgen.launcher.PROGRESS --es line \"$L\" >/dev/null 2>&1; echo \"$L\"; done\nam broadcast -a com.polgen.launcher.PROGRESS --es line '__DONE__' >/dev/null 2>&1\necho\necho '✅ Готово! Возвращайся в PolGen и нажми «Запустить PolGen».'"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->runCommand(Ljava/lang/String;)V
    return-void

    :not_install
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnRun:Landroid/widget/Button;
    if-ne p1, v0, :not_run

    const-string v0, "if [ -d $HOME/PolGen ]; then\n  am broadcast -a com.polgen.launcher.PROGRESS --es line '__START__ Запуск сервера PolGen…' >/dev/null 2>&1\n  cd $HOME/PolGen && bash android/run.sh\n  am broadcast -a com.polgen.launcher.PROGRESS --es line '__DONE__ Сервер остановлен' >/dev/null 2>&1\nelse\n  am broadcast -a com.polgen.launcher.PROGRESS --es line '__FAIL__ PolGen не найден — сначала установка' >/dev/null 2>&1\n  echo '❌ PolGen не найден. Сначала нажми «Установить / обновить PolGen».'\nfi"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->runCommand(Ljava/lang/String;)V
    return-void

    :not_run
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnOpen:Landroid/widget/Button;
    if-ne p1, v0, :not_open

    const-string v0, "http://127.0.0.1:4000"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->openUrl(Ljava/lang/String;)V
    return-void

    :not_open
    const-string v0, "am broadcast -a com.polgen.launcher.PROGRESS --es line '__START__ Установка PolGen начата' >/dev/null 2>&1\nmkdir -p $HOME/.termux\ntouch $HOME/.termux/termux.properties\ngrep -qs 'allow-external-apps' $HOME/.termux/termux.properties || echo 'allow-external-apps = true' >> $HOME/.termux/termux.properties\ncommand -v git >/dev/null 2>&1 || { am broadcast -a com.polgen.launcher.PROGRESS --es line '⚙ git: устанавливаем' >/dev/null 2>&1; pkg install -y git; }\nif [ -d $HOME/PolGen/.git ]; then\n  am broadcast -a com.polgen.launcher.PROGRESS --es line '⬇ PolGen: обновляем' >/dev/null 2>&1\n  cd $HOME/PolGen || { am broadcast -a com.polgen.launcher.PROGRESS --es line '__FAIL__' >/dev/null 2>&1; exit 1; }\n  git pull --ff-only || { git fetch --depth 1 origin && git reset --hard FETCH_HEAD; }\nelse\n  am broadcast -a com.polgen.launcher.PROGRESS --es line '⬇ PolGen: скачиваем репозиторий' >/dev/null 2>&1\n  rm -rf $HOME/PolGen\n  git clone --depth 1 -b arena/01a057f4-polgen https://github.com/Player124413/PolGen.git $HOME/PolGen || git clone --depth 1 https://github.com/Player124413/PolGen.git $HOME/PolGen || { am broadcast -a com.polgen.launcher.PROGRESS --es line '__FAIL__' >/dev/null 2>&1; exit 1; }\n  cd $HOME/PolGen || { am broadcast -a com.polgen.launcher.PROGRESS --es line '__FAIL__' >/dev/null 2>&1; exit 1; }\nfi\nam broadcast -a com.polgen.launcher.PROGRESS --es line '⚙ Зависимости: Python, PyTorch, FFmpeg, модели — это долго' >/dev/null 2>&1\nbash android/install.sh 2>&1 | while IFS= read -r L; do am broadcast -a com.polgen.launcher.PROGRESS --es line \"$L\" >/dev/null 2>&1; echo \"$L\"; done\nam broadcast -a com.polgen.launcher.PROGRESS --es line '__DONE__' >/dev/null 2>&1\necho\necho '✅ Готово! Возвращайся в PolGen и нажми «Запустить PolGen».'"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->copyToClipboard(Ljava/lang/String;)V

    const-string v0, "Команда скопирована — открой Termux и вставь (долгое нажатие → Вставить)"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->toast(Ljava/lang/String;)V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    invoke-virtual {v0}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v1
    const-string v2, "Ошибка: "
    invoke-virtual {v2, v1}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v1
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->toast(Ljava/lang/String;)V

    return-void
.end method


# public void onRequestPermissionsResult(int, String[], int[])
.method public onRequestPermissionsResult(I[Ljava/lang/String;[I)V
    .locals 2

    const/4 v0, 0x1
    if-ne p1, v0, :done

    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->pendingScript:Ljava/lang/String;
    if-eqz v0, :done

    if-eqz p3, :done

    array-length v1, p3
    if-lez v1, :done

    const/4 v1, 0x0
    aget v1, p3, v1
    if-nez v1, :done

    const/4 v1, 0x0
    iput-object v1, p0, Lcom/polgen/launcher/MainActivity;->pendingScript:Ljava/lang/String;

    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->runCommand(Ljava/lang/String;)V

    :done
    return-void
.end method
