import gradio as gr


def settings():
    with gr.Accordion("Настройки преобразования", open=False):
        with gr.Column(variant="panel"):
            with gr.Accordion("Стандартные настройки", open=False):
                with gr.Group():
                    with gr.Column(variant="panel"):
                        f0_method = gr.Dropdown(
                            value="rmvpe",
                            label="Метод выделения тона",
                            choices=["rmvpe+", "rmvpe", "fcpe", "crepe", "crepe-tiny"],
                            interactive=True,
                            visible=True,
                        )
                    with gr.Column(variant="panel"):
                        index_rate = gr.Slider(
                            minimum=0,
                            maximum=1,
                            step=0.01,
                            value=0,
                            label="Влияние индекса",
                            info="Влияние индексного файла. Чем выше — тем больше влияние. Низкие значения смягчают артефакты.",
                            interactive=True,
                            visible=True,
                        )
                        volume_envelope = gr.Slider(
                            minimum=0,
                            maximum=1,
                            step=0.01,
                            value=1,
                            label="Скорость смешивания RMS",
                            info="Чем ближе к 1, тем больше используется огибающая выходного сигнала.",
                            interactive=True,
                            visible=True,
                        )
                        protect = gr.Slider(
                            minimum=0,
                            maximum=0.5,
                            step=0.01,
                            value=0.5,
                            label="Защита согласных",
                            info="Защита согласных и дыхания от артефактов. 0.5 = полная защита.",
                            interactive=True,
                            visible=True,
                        )

            with gr.Accordion("Дополнительные настройки", open=False):
                with gr.Group():
                    with gr.Column():
                        with gr.Row(variant="panel"):
                            stereo_sound = gr.Checkbox(
                                value=False,
                                label="Преобразовать в стерео",
                                info="Преобразование моно звука в стерео",
                                interactive=True,
                                visible=True,
                            )
                            audio_upscaling = gr.Checkbox(
                                value=False,
                                label="Аудио-апскейл",
                                info="Улучшение качества аудио (долгая обработка)",
                                interactive=True,
                                visible=True,
                            )

                        # === AUTOTUNE ===
                        with gr.Column(variant="panel"):
                            autotune = gr.Checkbox(
                                value=False,
                                label="АвтоТюн",
                                info="Коррекция высоты тона к нотам гаммы",
                                interactive=True,
                                visible=True,
                            )
                            with gr.Column(visible=False) as autotune_settings:
                                with gr.Row():
                                    autotune_tonic = gr.Dropdown(
                                        value="C",
                                        label="Тоника",
                                        choices=[
                                            "C", "C#", "Db", "D", "D#", "Eb",
                                            "E", "F", "F#", "Gb", "G", "G#",
                                            "Ab", "A", "A#", "Bb", "B",
                                        ],
                                        interactive=True,
                                        visible=True,
                                    )
                                    autotune_scale = gr.Dropdown(
                                        value="chromatic",
                                        label="Гамма/Лад",
                                        choices=[
                                            "chromatic", "major", "minor",
                                            "dorian", "phrygian", "lydian",
                                            "mixolydian", "harmonic_minor",
                                            "melodic_minor", "pentatonic_major",
                                            "pentatonic_minor", "blues",
                                        ],
                                        interactive=True,
                                        visible=True,
                                    )
                                autotune_strength = gr.Slider(
                                    minimum=0,
                                    maximum=1,
                                    step=0.05,
                                    value=1.0,
                                    label="Сила коррекции",
                                    info="0 = без коррекции, 1 = полная коррекция",
                                    interactive=True,
                                    visible=True,
                                )
                                autotune_retune_speed = gr.Slider(
                                    minimum=0,
                                    maximum=400,
                                    step=10,
                                    value=0,
                                    label="Скорость коррекции (мс)",
                                    info="0 = мгновенно (эффект T-Pain), 50-100 = естественно, 200+ = мягко",
                                    interactive=True,
                                    visible=True,
                                )
                                autotune_flex_tune = gr.Slider(
                                    minimum=0,
                                    maximum=1,
                                    step=0.05,
                                    value=0,
                                    label="Flex-Tune",
                                    info="Умная коррекция: 0 = корректировать всё, 1 = только фальшивые ноты",
                                    interactive=True,
                                    visible=True,
                                )
                                autotune_preserve_vibrato = gr.Slider(
                                    minimum=0,
                                    maximum=1,
                                    step=0.05,
                                    value=0,
                                    label="Сохранение вибрато",
                                    info="0 = убрать вибрато, 1 = полностью сохранить",
                                    interactive=True,
                                    visible=True,
                                )
                                autotune_humanize = gr.Slider(
                                    minimum=0,
                                    maximum=1,
                                    step=0.05,
                                    value=0,
                                    label="Humanize",
                                    info="Добавляет микро-вариации для естественности",
                                    interactive=True,
                                    visible=True,
                                )

                        with gr.Row(variant="panel"):
                            f0_min = gr.Slider(
                                minimum=1,
                                maximum=120,
                                step=1,
                                value=50,
                                label="Минимальный диапазон тона",
                                info="Нижняя граница диапазона F0.",
                                interactive=True,
                                visible=True,
                            )
                            f0_max = gr.Slider(
                                minimum=380,
                                maximum=16000,
                                step=1,
                                value=1100,
                                label="Максимальный диапазон тона",
                                info="Верхняя граница диапазона F0.",
                                interactive=True,
                                visible=True,
                            )

    # Показать/скрыть настройки автотюна
    autotune.change(
        lambda x: gr.update(visible=x),
        inputs=autotune,
        outputs=autotune_settings,
    )

    return (
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
    )
