.class public Lcom/polgen/launcher/MainActivity;
.super Landroid/app/Activity;
.source "MainActivity.java"

# interfaces
.implements Landroid/view/View$OnClickListener;


# instance fields
.field private root:Landroid/widget/LinearLayout;
.field private status:Landroid/widget/TextView;
.field private btnInstall:Landroid/widget/Button;
.field private btnRun:Landroid/widget/Button;
.field private btnOpen:Landroid/widget/Button;
.field private btnTermux:Landroid/widget/Button;
.field private pendingScript:Ljava/lang/String;


# direct methods
.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Landroid/app/Activity;-><init>()V

    return-void
.end method


.method protected onCreate(Landroid/os/Bundle;)V
    .locals 10

    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    # ScrollView scroll = new ScrollView(this)
    new-instance v0, Landroid/widget/ScrollView;
    invoke-direct {v0, p0}, Landroid/widget/ScrollView;-><init>(Landroid/content/Context;)V

    # LinearLayout root = new LinearLayout(this)
    new-instance v1, Landroid/widget/LinearLayout;
    invoke-direct {v1, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V
    iput-object v1, p0, Lcom/polgen/launcher/MainActivity;->root:Landroid/widget/LinearLayout;

    # root.setOrientation(VERTICAL)
    const/4 v2, 0x1
    invoke-virtual {v1, v2}, Landroid/widget/LinearLayout;->setOrientation(I)V

    # тёмный фон для scroll и root (#FF10141A)
    const v2, -0xefebe6
    invoke-virtual {v0, v2}, Landroid/view/View;->setBackgroundColor(I)V
    invoke-virtual {v1, v2}, Landroid/view/View;->setBackgroundColor(I)V

    # int pad = dp(16); root.setPadding(pad,pad,pad,pad)
    const/16 v2, 0x10
    invoke-direct {p0, v2}, Lcom/polgen/launcher/MainActivity;->dp(I)I
    move-result v3
    invoke-virtual {v1, v3, v3, v3, v3}, Landroid/view/View;->setPadding(IIII)V

    # scroll.addView(root)
    invoke-virtual {v0, v1}, Landroid/widget/ScrollView;->addView(Landroid/view/View;)V

    # заголовок
    const-string v4, "PolGen"
    const/high16 v5, 0x41d00000    # 26.0f
    const v6, -0xb31f86            # 0xFF4CE07A
    invoke-direct {p0, v4, v5, v6}, Lcom/polgen/launcher/MainActivity;->addText(Ljava/lang/String;FI)Landroid/widget/TextView;

    # подзаголовок
    const-string v4, "Нейросетевая замена голоса — прямо на телефоне"
    const/high16 v5, 0x41500000    # 13.0f
    const v6, -0x776656            # 0xFF8899AA
    invoke-direct {p0, v4, v5, v6}, Lcom/polgen/launcher/MainActivity;->addText(Ljava/lang/String;FI)Landroid/widget/TextView;

    # строка статуса
    const-string v4, ""
    const/high16 v5, 0x41600000    # 14.0f
    const v6, -0x222223            # 0xFFDDDDDD
    invoke-direct {p0, v4, v5, v6}, Lcom/polgen/launcher/MainActivity;->addText(Ljava/lang/String;FI)Landroid/widget/TextView;
    move-result-object v7
    iput-object v7, p0, Lcom/polgen/launcher/MainActivity;->status:Landroid/widget/TextView;

    # if (isTermuxInstalled()) {...} else {...}
    invoke-direct {p0}, Lcom/polgen/launcher/MainActivity;->isTermuxInstalled()Z
    move-result v8
    if-eqz v8, :no_termux

    const-string v9, "Termux найден ✓"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->setStatus(Ljava/lang/String;)V

    const-string v9, "🚀  Установить / обновить PolGen"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnInstall:Landroid/widget/Button;

    const-string v9, "▶  Запустить PolGen"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnRun:Landroid/widget/Button;

    const-string v9, "🌐  Открыть интерфейс"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnOpen:Landroid/widget/Button;

    const-string v9, "📋  Скопировать команду установки"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    goto :after_buttons

    :no_termux
    const-string v9, "Сначала установи Termux (кнопка ниже), затем вернись сюда и нажми «Установить PolGen»."
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->setStatus(Ljava/lang/String;)V

    const-string v9, "⬇️  Шаг 1 · Установить Termux (F-Droid)"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;
    move-result-object v9
    iput-object v9, p0, Lcom/polgen/launcher/MainActivity;->btnTermux:Landroid/widget/Button;

    const-string v9, "📋  Скопировать команду установки"
    invoke-direct {p0, v9}, Lcom/polgen/launcher/MainActivity;->addButton(Ljava/lang/String;)Landroid/widget/Button;

    :after_buttons
    # подсказка внизу
    const-string v4, "Если после нажатия ничего не произошло — Termux запрещает автозапуск. Вставь скопированную команду в Termux (долгое нажатие → Вставить) один раз, дальше всё будет работать автоматически."
    const/high16 v5, 0x41400000    # 12.0f
    const v6, -0x998878            # 0xFF667788
    invoke-direct {p0, v4, v5, v6}, Lcom/polgen/launcher/MainActivity;->addText(Ljava/lang/String;FI)Landroid/widget/TextView;

    # setContentView(scroll)
    invoke-virtual {p0, v0}, Landroid/app/Activity;->setContentView(Landroid/view/View;)V

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


# void setStatus(String text)
.method private setStatus(Ljava/lang/String;)V
    .locals 1

    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->status:Landroid/widget/TextView;
    if-eqz v0, :skip

    invoke-virtual {v0, p1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V

    :skip
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


# void runCommand(String script) — отправка RUN_COMMAND в Termux
.method private runCommand(Ljava/lang/String;)V
    .locals 4

    # разрешение RUN_COMMAND получено?
    const-string v0, "com.termux.permission.RUN_COMMAND"
    invoke-virtual {p0, v0}, Landroid/content/Context;->checkSelfPermission(Ljava/lang/String;)I
    move-result v1
    if-eqz v1, :granted

    # нет — запросим и запомним скрипт
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
    # Intent("com.termux.RUN_COMMAND")
    new-instance v0, Landroid/content/Intent;
    const-string v1, "com.termux.RUN_COMMAND"
    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    # setComponent(com.termux / RunCommandService)
    new-instance v1, Landroid/content/ComponentName;
    const-string v2, "com.termux"
    const-string v3, "com.termux.app.RunCommandService"
    invoke-direct {v1, v2, v3}, Landroid/content/ComponentName;-><init>(Ljava/lang/String;Ljava/lang/String;)V
    invoke-virtual {v0, v1}, Landroid/content/Intent;->setComponent(Landroid/content/ComponentName;)Landroid/content/Intent;

    # RUN_COMMAND_PATH = bash
    const-string v1, "/data/data/com.termux/files/usr/bin/bash"
    const-string v2, "com.termux.RUN_COMMAND_PATH"
    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;

    # RUN_COMMAND_ARGUMENTS = ["-c", script]
    const/4 v1, 0x2
    new-array v1, v1, [Ljava/lang/String;
    const/4 v2, 0x0
    const-string v3, "-c"
    aput-object v3, v1, v2
    const/4 v2, 0x1
    aput-object p1, v1, v2
    const-string v2, "com.termux.RUN_COMMAND_ARGUMENTS"
    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;[Ljava/lang/String;)Landroid/content/Intent;

    # RUN_COMMAND_WORKDIR = home
    const-string v1, "/data/data/com.termux/files/home"
    const-string v2, "com.termux.RUN_COMMAND_WORKDIR"
    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;

    # startService(intent)
    :try_start_0
    invoke-virtual {p0, v0}, Landroid/app/Activity;->startService(Landroid/content/Intent;)Landroid/content/ComponentName;
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_fail

    const-string v1, "Команда отправлена — смотри окно Termux."
    invoke-direct {p0, v1}, Lcom/polgen/launcher/MainActivity;->setStatus(Ljava/lang/String;)V

    # открыть Termux поверх, чтобы было видно прогресс
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
    # Termux не установлен → открыть F-Droid
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnTermux:Landroid/widget/Button;
    if-ne p1, v0, :not_termux

    const-string v0, "https://f-droid.org/packages/com.termux/"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->openUrl(Ljava/lang/String;)V
    return-void

    :not_termux
    # Установить / обновить
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnInstall:Landroid/widget/Button;
    if-ne p1, v0, :not_install

    const-string v0, "mkdir -p $HOME/.termux\ntouch $HOME/.termux/termux.properties\ngrep -qs 'allow-external-apps' $HOME/.termux/termux.properties || echo 'allow-external-apps = true' >> $HOME/.termux/termux.properties\ncommand -v git >/dev/null 2>&1 || pkg install -y git\nif [ -d $HOME/PolGen/.git ]; then\n  cd $HOME/PolGen || exit 1\n  git pull --ff-only || { git fetch --depth 1 origin && git reset --hard FETCH_HEAD; }\nelse\n  rm -rf $HOME/PolGen\n  git clone --depth 1 -b arena/01a057f4-polgen https://github.com/Player124413/PolGen.git $HOME/PolGen || git clone --depth 1 https://github.com/Player124413/PolGen.git $HOME/PolGen || exit 1\n  cd $HOME/PolGen || exit 1\nfi\nbash android/install.sh\necho\necho '✅ Готово! Возвращайся в приложение PolGen и нажми «Запустить PolGen».'"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->runCommand(Ljava/lang/String;)V
    return-void

    :not_install
    # Запустить
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnRun:Landroid/widget/Button;
    if-ne p1, v0, :not_run

    const-string v0, "if [ -d $HOME/PolGen ]; then cd $HOME/PolGen && bash android/run.sh; else echo '❌ PolGen не найден. Сначала нажми «Установить / обновить PolGen».'; fi"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->runCommand(Ljava/lang/String;)V
    return-void

    :not_run
    # Открыть интерфейс
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity;->btnOpen:Landroid/widget/Button;
    if-ne p1, v0, :not_open

    const-string v0, "http://127.0.0.1:4000"
    invoke-direct {p0, v0}, Lcom/polgen/launcher/MainActivity;->openUrl(Ljava/lang/String;)V
    return-void

    :not_open
    # осталась кнопка «Скопировать команду»
    const-string v0, "mkdir -p $HOME/.termux\ntouch $HOME/.termux/termux.properties\ngrep -qs 'allow-external-apps' $HOME/.termux/termux.properties || echo 'allow-external-apps = true' >> $HOME/.termux/termux.properties\ncommand -v git >/dev/null 2>&1 || pkg install -y git\nif [ -d $HOME/PolGen/.git ]; then\n  cd $HOME/PolGen || exit 1\n  git pull --ff-only || { git fetch --depth 1 origin && git reset --hard FETCH_HEAD; }\nelse\n  rm -rf $HOME/PolGen\n  git clone --depth 1 -b arena/01a057f4-polgen https://github.com/Player124413/PolGen.git $HOME/PolGen || git clone --depth 1 https://github.com/Player124413/PolGen.git $HOME/PolGen || exit 1\n  cd $HOME/PolGen || exit 1\nfi\nbash android/install.sh\necho\necho '✅ Готово! Возвращайся в приложение PolGen и нажми «Запустить PolGen».'"
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
