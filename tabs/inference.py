import gradio as gr

from rvc.infer.infer import rvc_edgetts_infer, rvc_infer
from tabs.components.modules import (
    OUTPUT_FORMAT,
    edge_voices,
    get_folders,
    process_file_upload,
    swap_buttons,
    swap_visibility,
    update_edge_voices,
    update_models_list,
)
from tabs.components.settings import settings


# Типы голосов для AutoPitch
VOICE_TYPES = [
    ("Бас (низкий мужской)", "bass"),
    ("Баритон (средний мужской)", "baritone"),
    ("Тенор (высокий мужской)", "tenor"),
    ("Альт (низкий женский)", "alto"),
    ("Сопрано (высокий женский)", "soprano"),
]


def inference_tab():
    with gr.Row():
        with gr.Column(scale=1, variant="panel"):
            with gr.Group():
                rvc_model = gr.Dropdown(
                    label="Голосовые модели:",
                    choices=get_folders(),
                    interactive=True,
                    visible=True,
                )
                ref_btn = gr.Button(
                    value="Обновить список моделей",
                    variant="primary",
                    interactive=True,
                    visible=True,
                )
            with gr.Group():
                autopitch = gr.Checkbox(
                    value=False,
                    label="Автоматическое определение высоты тона",
                    interactive=True,
                    visible=True,
                )
                autopitch_model_type = gr.Dropdown(
                    value="baritone",
                    label="Тип голоса модели",
                    choices=VOICE_TYPES,
                    interactive=True,
                    visible=False,
                )
                rvc_pitch = gr.Slider(
                    minimum=-24,
                    maximum=24,
                    step=1,
                    value=0,
                    label="Регулировка высоты тона",
                    info="-24 — ниже | +24 — выше",
                    interactive=True,
                    visible=True,
                )

        with gr.Column(scale=2, variant="panel"):
            with gr.Column() as upload_file:
                local_file = gr.Audio(
                    label="Аудио",
                    type="filepath",
                    show_download_button=False,
                    show_share_button=False,
                    interactive=True,
                    visible=True,
                )

            with gr.Column(visible=False) as enter_local_file:
                song_input = gr.Text(
                    label="Путь к файлу:",
                    info="Введите полный путь к файлу.",
                    interactive=True,
                    visible=True,
                )

            with gr.Column():
                show_upload_button = gr.Button(
                    value="Загрузить файл с устройства",
                    interactive=True,
                    visible=False,
                )
                show_enter_button = gr.Button(
                    value="Ввести путь к файлу",
                    interactive=True,
                    visible=True,
                )

    with gr.Group():
        with gr.Row(equal_height=True):
            generate_btn = gr.Button(
                value="Генерировать",
                variant="primary",
                interactive=True,
                visible=True,
                scale=2,
            )
            converted_voice = gr.Audio(
                label="Преобразованный голос",
                show_download_button=True,
                show_share_button=False,
                interactive=False,
                visible=True,
                scale=9,
            )
            with gr.Column(min_width=160):
                output_format = gr.Dropdown(
                    value="mp3",
                    label="Формат файла",
                    choices=OUTPUT_FORMAT,
                    interactive=True,
                    visible=True,
                )

    # Компонент настроек
    (
        f0_method,
        index_rate,
        volume_envelope,
        protect,
        stereo_sound,
        audio_upscaling,
        autotune,
        autotune_tonic,
        autotune_scale,
        autotune_strength,
        autotune_retune_speed,
        autotune_flex_tune,
        autotune_preserve_vibrato,
        autotune_humanize,
        f0_min,
        f0_max,
    ) = settings()

    # Загрузка файлов
    local_file.input(process_file_upload, inputs=[local_file], outputs=[song_input, local_file])

    # Обновление кнопок
    show_upload_button.click(swap_visibility, outputs=[upload_file, enter_local_file, song_input, local_file])
    show_enter_button.click(swap_visibility, outputs=[enter_local_file, upload_file, song_input, local_file])
    show_upload_button.click(swap_buttons, outputs=[show_upload_button, show_enter_button])
    show_enter_button.click(swap_buttons, outputs=[show_enter_button, show_upload_button])

    # Показать/скрыть тип голоса модели при включении autopitch
    autopitch.change(
        lambda x: (gr.update(visible=x), gr.update(visible=not x)),
        inputs=autopitch,
        outputs=[autopitch_model_type, rvc_pitch],
    )

    # Обновление списка моделей
    ref_btn.click(update_models_list, None, outputs=rvc_model)

    # Запуск процесса преобразования
    generate_btn.click(
        rvc_infer,
        inputs=[
            rvc_model,
            song_input,
            f0_method,
            f0_min,
            f0_max,
            rvc_pitch,
            protect,
            index_rate,
            volume_envelope,
            autopitch,
            autopitch_model_type,
            autotune,
            autotune_tonic,
            autotune_scale,
            autotune_strength,
            autotune_retune_speed,
            autotune_flex_tune,
            autotune_preserve_vibrato,
            autotune_humanize,
            audio_upscaling,
            stereo_sound,
            output_format,
        ],
        outputs=[converted_voice],
    )


def edge_tts_tab():
    with gr.Row():
        with gr.Column(variant="panel", scale=1):
            with gr.Group():
                rvc_model = gr.Dropdown(
                    label="Голосовые модели:",
                    choices=get_folders(),
                    interactive=True,
                    visible=True,
                )
                ref_btn = gr.Button(
                    value="Обновить список моделей",
                    variant="primary",
                    interactive=True,
                    visible=True,
                )
            with gr.Group():
                language = gr.Dropdown(
                    label="Язык",
                    choices=list(edge_voices.keys()),
                    interactive=True,
                    visible=True,
                )
                tts_voice = gr.Dropdown(
                    value="en-GB-SoniaNeural",
                    label="Голос",
                    choices=["en-GB-SoniaNeural", "en-GB-RyanNeural"],
                    interactive=True,
                    visible=True,
                )
        with gr.Column(variant="panel", scale=2):
            with gr.Column():
                with gr.Group():
                    autopitch = gr.Checkbox(
                        value=False,
                        label="Автоматическое определение высоты тона",
                        interactive=True,
                        visible=True,
                    )
                    autopitch_model_type = gr.Dropdown(
                        value="baritone",
                        label="Тип голоса модели",
                        choices=VOICE_TYPES,
                        interactive=True,
                        visible=False,
                    )
                    rvc_pitch = gr.Slider(
                        minimum=-24,
                        maximum=24,
                        step=1,
                        value=0,
                        label="Регулировка высоты тона",
                        info="-24 — ниже | +24 — выше",
                        interactive=True,
                        visible=True,
                    )
            synth_voice = gr.Audio(
                label="Синтезированный TTS голос",
                show_download_button=True,
                show_share_button=False,
                interactive=False,
                visible=True,
            )

    with gr.Accordion("Настройки синтеза речи", open=False):
        with gr.Group():
            with gr.Row():
                tts_pitch = gr.Slider(
                    minimum=-100,
                    maximum=100,
                    step=1,
                    value=0,
                    label="Регулировка высоты тона TTS",
                    info="-100 — ниже | +100 — выше",
                    interactive=True,
                    visible=True,
                )
                tts_volume = gr.Slider(
                    minimum=-100,
                    maximum=100,
                    step=1,
                    value=0,
                    label="Громкость речи",
                    info="Громкость синтеза речи",
                    interactive=True,
                    visible=True,
                )
                tts_rate = gr.Slider(
                    minimum=-100,
                    maximum=100,
                    step=1,
                    value=0,
                    label="Скорость речи",
                    info="Скорость синтеза речи",
                    interactive=True,
                    visible=True,
                )

    tts_text = gr.Textbox(label="Введите текст", lines=5)

    with gr.Group():
        with gr.Row(equal_height=True):
            generate_btn = gr.Button(
                value="Генерировать",
                variant="primary",
                interactive=True,
                visible=True,
                scale=2,
            )
            converted_synth_voice = gr.Audio(
                label="Преобразованный TTS голос",
                show_download_button=True,
                show_share_button=False,
                interactive=False,
                visible=True,
                scale=9,
            )
            with gr.Column(min_width=160):
                output_format = gr.Dropdown(
                    value="mp3",
                    label="Формат файла",
                    choices=OUTPUT_FORMAT,
                    interactive=True,
                    visible=True,
                )

    # Компонент настроек
    (
        f0_method,
        index_rate,
        volume_envelope,
        protect,
        stereo_sound,
        audio_upscaling,
        autotune,
        autotune_tonic,
        autotune_scale,
        autotune_strength,
        autotune_retune_speed,
        autotune_flex_tune,
        autotune_preserve_vibrato,
        autotune_humanize,
        f0_min,
        f0_max,
    ) = settings()

    # Обновление списка TTS-голосов
    language.change(update_edge_voices, inputs=language, outputs=tts_voice)

    # Показать/скрыть тип голоса модели при включении autopitch
    autopitch.change(
        lambda x: (gr.update(visible=x), gr.update(visible=not x)),
        inputs=autopitch,
        outputs=[autopitch_model_type, rvc_pitch],
    )

    # Обновление списка моделей
    ref_btn.click(update_models_list, None, outputs=rvc_model)

    # Запуск процесса преобразования
    generate_btn.click(
        rvc_edgetts_infer,
        inputs=[
            rvc_model,
            f0_method,
            f0_min,
            f0_max,
            rvc_pitch,
            protect,
            index_rate,
            volume_envelope,
            autopitch,
            autopitch_model_type,
            autotune,
            autotune_tonic,
            autotune_scale,
            autotune_strength,
            autotune_retune_speed,
            autotune_flex_tune,
            autotune_preserve_vibrato,
            autotune_humanize,
            stereo_sound,
            output_format,
            tts_voice,
            tts_text,
            tts_rate,
            tts_volume,
            tts_pitch,
            audio_upscaling,
        ],
        outputs=[synth_voice, converted_synth_voice],
    )
