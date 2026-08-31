.class public Lcom/polgen/launcher/MainActivity$InstallRunnable;
.super Ljava/lang/Object;
.source "MainActivity.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Lcom/polgen/launcher/MainActivity;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x1
    name = "InstallRunnable"
.end annotation


# instance fields
.field private final activity:Lcom/polgen/launcher/MainActivity;


# direct methods
.method public constructor <init>(Lcom/polgen/launcher/MainActivity;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/polgen/launcher/MainActivity$InstallRunnable;->activity:Lcom/polgen/launcher/MainActivity;

    return-void
.end method


# private methods

# void report(String line) — потокобезопасная отправка строки в журнал (через runOnUiThread)
.method private report(Ljava/lang/String;)V
    .locals 3

    :try_start_0
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity$InstallRunnable;->activity:Lcom/polgen/launcher/MainActivity;
    if-eqz v0, :done

    new-instance v1, Lcom/polgen/launcher/MainActivity$LogRunnable;
    invoke-direct {v1, v0, p1}, Lcom/polgen/launcher/MainActivity$LogRunnable;-><init>(Lcom/polgen/launcher/MainActivity;Ljava/lang/String;)V

    invoke-virtual {v0, v1}, Landroid/app/Activity;->runOnUiThread(Ljava/lang/Runnable;)V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    :catch_0
    :done
    return-void
.end method


# virtual methods

# Установка встроенного termux.apk через PackageInstaller (в фоновом потоке)
.method public run()V
    .locals 10

    const/4 v0, 0x0                # InputStream in = null

    :try_start_0
    iget-object v1, p0, Lcom/polgen/launcher/MainActivity$InstallRunnable;->activity:Lcom/polgen/launcher/MainActivity;
    invoke-virtual {v1}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
    move-result-object v1
    const-string v2, "termux.apk"
    invoke-virtual {v1, v2}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v0

    iget-object v1, p0, Lcom/polgen/launcher/MainActivity$InstallRunnable;->activity:Lcom/polgen/launcher/MainActivity;
    invoke-virtual {v1}, Landroid/app/Activity;->getPackageManager()Landroid/content/pm/PackageManager;
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

    iget-object v7, p0, Lcom/polgen/launcher/MainActivity$InstallRunnable;->activity:Lcom/polgen/launcher/MainActivity;
    const/4 v5, 0x2
    const v6, 0xa000000               # FLAG_UPDATE_CURRENT | FLAG_MUTABLE
    invoke-static {v7, v5, v4, v6}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;
    move-result-object v4
    invoke-virtual {v4}, Landroid/app/PendingIntent;->getIntentSender()Landroid/content/IntentSender;
    move-result-object v4
    invoke-virtual {v2, v4}, Landroid/content/pm/PackageInstaller$Session;->commit(Landroid/content/IntentSender;)V

    const-string v5, "\u23f3 Termux: подтверди установку в появившемся системном окне\u2026"
    invoke-direct {p0, v5}, Lcom/polgen/launcher/MainActivity$InstallRunnable;->report(Ljava/lang/String;)V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_all

    return-void

    :catch_all
    move-exception v4

    :try_start_1
    if-eqz v0, :skip_close
    invoke-virtual {v0}, Ljava/io/InputStream;->close()V
    :skip_close
    :try_end_1
    .catch Ljava/lang/Throwable; {:try_start_1 .. :try_end_1} :catch_1

    :catch_1
    invoke-virtual {v4}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v5
    const-string v6, "\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0438 Termux: "
    invoke-virtual {v6, v5}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v5
    invoke-direct {p0, v5}, Lcom/polgen/launcher/MainActivity$InstallRunnable;->report(Ljava/lang/String;)V

    return-void
.end method
