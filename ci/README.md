# 🔄 CI-workflows PolGen

GitHub Actions читает workflows **только** из `.github/workflows/`, но у
бота, который пушит изменения в эту ветку, нет права менять файлы workflows.
Поэтому готовые workflows лежат здесь, в `ci/`, и активируются одним
копированием.

## 📱 `standalone-apk.yml` — автономный APK (без Termux)

Собирает APK, внутри которого **всё ядро PolGen**: Python 3.8, PyTorch
1.8.1 (arm64), scipy, edge-tts и веб-интерфейс. Termux не нужен вообще.
Результат выкладывается **артефактом** (релизы не создаются).

### Как включить (один раз, 30 секунд)

1. Открой [standalone-apk.yml](standalone-apk.yml) на GitHub и скопируй
   его содержимое (кнопка «Copy raw contents»).
2. В репозитории: **Add file → Create new file** → имя
   `.github/workflows/standalone-apk.yml` → вставь → **Commit**.
3. Вкладка **Actions** → «PolGen standalone APK» → **Run workflow** →
   выбери ветку → Run.
4. Через ~10 минут: страница запуска → **Artifacts** →
   `PolGen-standalone-apk` → скачай zip, внутри `PolGen-standalone.apk`.

APK подписан тем же ключом, что и предыдущие версии лаунчера, поэтому
ставится поверх без удаления.

### Старый workflow

Если в `.github/workflows/main.yml` остался прежний лаунчер со встроенным
Termux — его можно удалить (он больше не собирается: `android/apk/`
удалён вместе с Termux-частью).
