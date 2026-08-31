.class public Lcom/polgen/launcher/MainActivity$ProgressReceiver;
.super Landroid/content/BroadcastReceiver;
.source "MainActivity.java"


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Lcom/polgen/launcher/MainActivity;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x1
    name = "ProgressReceiver"
.end annotation


# instance fields
.field private final activity:Lcom/polgen/launcher/MainActivity;


# direct methods
.method public constructor <init>(Lcom/polgen/launcher/MainActivity;)V
    .locals 0

    invoke-direct {p0}, Landroid/content/BroadcastReceiver;-><init>()V

    iput-object p1, p0, Lcom/polgen/launcher/MainActivity$ProgressReceiver;->activity:Lcom/polgen/launcher/MainActivity;

    return-void
.end method


# virtual methods
.method public onReceive(Landroid/content/Context;Landroid/content/Intent;)V
    .locals 3

    if-eqz p2, :done

    invoke-virtual {p2}, Landroid/content/Intent;->getAction()Ljava/lang/String;
    move-result-object v0

    const-string v1, "com.polgen.launcher.PROGRESS"
    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v2
    if-eqz v2, :not_progress

    const-string v1, "line"
    invoke-virtual {p2, v1}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v1
    if-eqz v1, :done

    iget-object v2, p0, Lcom/polgen/launcher/MainActivity$ProgressReceiver;->activity:Lcom/polgen/launcher/MainActivity;
    if-eqz v2, :done

    invoke-virtual {v2, v1}, Lcom/polgen/launcher/MainActivity;->appendLog(Ljava/lang/String;)V
    return-void

    :not_progress
    const-string v1, "com.polgen.launcher.INSTALL_STATUS"
    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v2
    if-eqz v2, :done

    iget-object v2, p0, Lcom/polgen/launcher/MainActivity$ProgressReceiver;->activity:Lcom/polgen/launcher/MainActivity;
    if-eqz v2, :done

    invoke-virtual {v2, p2}, Lcom/polgen/launcher/MainActivity;->handleInstallStatus(Landroid/content/Intent;)V

    :done
    return-void
.end method
