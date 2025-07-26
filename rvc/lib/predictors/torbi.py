import math
from typing import Optional

import torch


def decode(
    observation: torch.Tensor,
    batch_frames: torch.Tensor,
    transition: torch.Tensor,
    initial: torch.Tensor,
    num_threads: int = 0,
) -> torch.Tensor:
    if observation.device.type == 'cpu':
        torch.set_num_threads(num_threads)
    return torch.ops.torbi.viterbi_decode(observation, batch_frames, transition, initial)


def from_probabilities(
    observation: torch.Tensor,
    batch_frames: Optional[torch.Tensor] = None,
    transition: Optional[torch.Tensor] = None,
    initial: Optional[torch.Tensor] = None,
    log_probs: bool = False,
    gpu: Optional[int] = None,
    num_threads: Optional[int] = 1
) -> torch.Tensor:
    batch, frames, states = observation.shape
    device = 'cpu' if gpu is None else f'cuda:{gpu}'

    if batch_frames is None:
        batch_frames = torch.full(
            (batch,),
            frames,
            dtype=torch.int32,
            device=device)
    batch_frames = batch_frames.to(dtype=torch.int32, device=device)

    # Default to uniform initial probabilities
    if initial is None:
        initial = torch.full(
            (states,),
            math.log((1. / states) + torch.finfo(torch.float32).tiny),
            dtype=torch.float32,
            device=device)

    # Ensure initial probabilities are in log space
    else:
        if not log_probs:
            initial = torch.log(initial)
        initial = initial.to(device)

    # Default to uniform transition probabilities
    if transition is None:
        transition = torch.full(
            (states, states),
            math.log(1. / states),
            dtype=torch.float32,
            device=device)

    # Ensure transition probabilities are in log space
    else:
        if not log_probs:
            transition = torch.log(transition)
        transition = transition.to(device)

    # Ensure observation probabilities are in log space
    if not log_probs:
        observation = torch.log(observation)
    observation = observation.to(device=device, dtype=torch.float32)

    # Add epsilon for stability
    # NOTE - may break gradients
    torch.exp_(observation)
    observation += torch.finfo(torch.float32).tiny
    torch.log_(observation)

    # Decode
    indices = decode(observation, batch_frames, transition, initial, num_threads=num_threads)
    return indices