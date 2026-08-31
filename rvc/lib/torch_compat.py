"""Совместимость RVC-кода со старыми сборками PyTorch.

В APK (Chaquopy) используется torch 1.8.1 — последний, для которого есть
Android-сборка. В нём weight_norm лежит в torch.nn.utils, а «новый»
параметризованный вариант (torch.nn.utils.parametrizations) появился
только в 1.12. Здесь — единая точка выбора.
"""

import torch.nn.utils

try:  # torch >= 1.12
    from torch.nn.utils.parametrizations import weight_norm  # noqa: F401
except ImportError:  # torch < 1.12 (в т.ч. Android-сборка 1.8.1)
    from torch.nn.utils import weight_norm  # noqa: F401
