.class public Lcom/polgen/launcher/MainActivity$CrashHandler;
.super Ljava/lang/Object;
.source "MainActivity.java"

# interfaces
.implements Ljava/lang/Thread$UncaughtExceptionHandler;


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Lcom/polgen/launcher/MainActivity;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x1
    name = "CrashHandler"
.end annotation


# instance fields
.field private final activity:Lcom/polgen/launcher/MainActivity;
.field private final prev:Ljava/lang/Thread$UncaughtExceptionHandler;


# direct methods
.method public constructor <init>(Lcom/polgen/launcher/MainActivity;Ljava/lang/Thread$UncaughtExceptionHandler;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/polgen/launcher/MainActivity$CrashHandler;->activity:Lcom/polgen/launcher/MainActivity;
    iput-object p2, p0, Lcom/polgen/launcher/MainActivity$CrashHandler;->prev:Ljava/lang/Thread$UncaughtExceptionHandler;

    return-void
.end method


# virtual methods

# Любая необработанная ошибка: logcat + файл crash.txt + тост с причиной
.method public uncaughtException(Ljava/lang/Thread;Ljava/lang/Throwable;)V
    .locals 6

    # 1) logcat
    :try_start_0
    const-string v0, "PolGen"
    const-string v1, "CRASH"
    invoke-static {v0, v1, p2}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0
    :catch_0

    # 2) трассировка в <внешние файлы приложения>/crash.txt
    :try_start_1
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity$CrashHandler;->activity:Lcom/polgen/launcher/MainActivity;
    if-eqz v0, :no_file

    const/4 v1, 0x0
    invoke-virtual {v0, v1}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v1
    if-eqz v1, :no_file

    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    invoke-virtual {v1}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;
    move-result-object v3
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v2
    const-string v3, "/crash.txt"
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v2
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v2

    new-instance v4, Ljava/io/FileWriter;
    const/4 v5, 0x1
    invoke-direct {v4, v2, v5}, Ljava/io/FileWriter;-><init>(Ljava/lang/String;Z)V
    new-instance v3, Ljava/io/PrintWriter;
    invoke-direct {v3, v4}, Ljava/io/PrintWriter;-><init>(Ljava/io/Writer;)V

    invoke-virtual {p2, v3}, Ljava/lang/Throwable;->printStackTrace(Ljava/io/PrintWriter;)V
    invoke-virtual {v3}, Ljava/io/PrintWriter;->close()V
    :try_end_1
    .catch Ljava/lang/Throwable; {:try_start_1 .. :try_end_1} :catch_1

    :catch_1
    :no_file

    # 3) тост с причиной (на Android 11+ рендерится системой и остаётся после смерти приложения)
    :try_start_2
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity$CrashHandler;->activity:Lcom/polgen/launcher/MainActivity;
    if-eqz v0, :no_toast

    new-instance v1, Ljava/lang/StringBuilder;
    const-string v2, "PolGen \u0430\u0432\u0430\u0440\u0438\u0439\u043d\u043e \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043b\u0441\u044f: "
    invoke-direct {v1, v2}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V
    invoke-virtual {p2}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    move-result-object v1
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1

    const/4 v2, 0x1                # Toast.LENGTH_LONG
    invoke-static {v0, v1, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v1
    invoke-virtual {v1}, Landroid/widget/Toast;->show()V
    :try_end_2
    .catch Ljava/lang/Throwable; {:try_start_2 .. :try_end_2} :catch_2

    :catch_2
    :no_toast

    # 4) передать системному обработчику (настоящее завершение)
    :try_start_3
    iget-object v0, p0, Lcom/polgen/launcher/MainActivity$CrashHandler;->prev:Ljava/lang/Thread$UncaughtExceptionHandler;
    if-eqz v0, :done
    invoke-interface {v0, p1, p2}, Ljava/lang/Thread$UncaughtExceptionHandler;->uncaughtException(Ljava/lang/Thread;Ljava/lang/Throwable;)V
    :try_end_3
    .catch Ljava/lang/Throwable; {:try_start_3 .. :try_end_3} :catch_3

    :catch_3
    :done
    return-void
.end method
