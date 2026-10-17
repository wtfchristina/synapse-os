#include "synapse_biquad.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

#if defined(__ARM_NEON) || defined(__ARM_NEON__)
#include <arm_neon.h>
#endif

int synapse_biquad_cascade_init(synapse_biquad_cascade_t *cascade,
                                uint32_t num_channels,
                                uint32_t num_sections,
                                const synapse_biquad_coeffs_t *coeffs) {
    if (!cascade || num_channels == 0 || num_sections == 0 || !coeffs) {
        return -1;
    }

    for (uint32_t s = 0; s < num_sections; ++s) {
        if (!synapse_biquad_verify_stability(&coeffs[s])) {
            return -2;
        }
    }

    cascade->num_channels = num_channels;
    cascade->num_sections = num_sections;

    cascade->coeffs = (synapse_biquad_coeffs_t *)malloc(num_sections * sizeof(synapse_biquad_coeffs_t));
    if (!cascade->coeffs) {
        return -3;
    }
    memcpy(cascade->coeffs, coeffs, num_sections * sizeof(synapse_biquad_coeffs_t));

    size_t total_states = (size_t)num_channels * (size_t)num_sections;
    cascade->states = (synapse_biquad_state_t *)malloc(total_states * sizeof(synapse_biquad_state_t));
    if (!cascade->states) {
        free(cascade->coeffs);
        cascade->coeffs = NULL;
        return -4;
    }

    memset(cascade->states, 0, total_states * sizeof(synapse_biquad_state_t));
    return 0;
}

void synapse_biquad_cascade_free(synapse_biquad_cascade_t *cascade) {
    if (cascade) {
        if (cascade->coeffs) {
            free(cascade->coeffs);
            cascade->coeffs = NULL;
        }
        if (cascade->states) {
            free(cascade->states);
            cascade->states = NULL;
        }
        cascade->num_channels = 0;
        cascade->num_sections = 0;
    }
}

void synapse_biquad_cascade_reset(synapse_biquad_cascade_t *cascade) {
    if (cascade && cascade->states) {
        size_t total_states = (size_t)cascade->num_channels * (size_t)cascade->num_sections;
        memset(cascade->states, 0, total_states * sizeof(synapse_biquad_state_t));
    }
}

bool synapse_biquad_verify_stability(const synapse_biquad_coeffs_t *coeffs) {
    if (!coeffs) {
        return false;
    }

    float a1 = coeffs->a1;
    float a2 = coeffs->a2;

    if (fabsf(a2) >= 1.0f) {
        return false;
    }
    if ((1.0f + a1 + a2) <= 0.0f) {
        return false;
    }
    if ((1.0f - a1 + a2) <= 0.0f) {
        return false;
    }

    return true;
}

void synapse_biquad_process_sample(synapse_biquad_cascade_t *cascade,
                                   const float *in_frame,
                                   float *out_frame) {
    const uint32_t n_ch = cascade->num_channels;
    const uint32_t n_sec = cascade->num_sections;

    for (uint32_t ch = 0; ch < n_ch; ++ch) {
        float x = in_frame[ch];
        synapse_biquad_state_t *ch_states = &cascade->states[ch * n_sec];

        for (uint32_t s = 0; s < n_sec; ++s) {
            const synapse_biquad_coeffs_t *c = &cascade->coeffs[s];
            synapse_biquad_state_t *st = &ch_states[s];

            float y = c->b0 * x + st->s1;
            st->s1 = c->b1 * x - c->a1 * y + st->s2;
            st->s2 = c->b2 * x - c->a2 * y;

            x = y;
        }

        out_frame[ch] = x;
    }
}

void synapse_biquad_process_block(synapse_biquad_cascade_t *cascade,
                                  uint32_t channel_idx,
                                  const float *in_samples,
                                  float *out_samples,
                                  size_t num_samples) {
    if (channel_idx >= cascade->num_channels || num_samples == 0) {
        return;
    }

    const uint32_t n_sec = cascade->num_sections;
    synapse_biquad_state_t *ch_states = &cascade->states[channel_idx * n_sec];

    if (in_samples != out_samples) {
        memcpy(out_samples, in_samples, num_samples * sizeof(float));
    }

    for (uint32_t s = 0; s < n_sec; ++s) {
        const synapse_biquad_coeffs_t c = cascade->coeffs[s];
        synapse_biquad_state_t st = ch_states[s];

        size_t n = 0;
        for (; n < num_samples; ++n) {
            float x = out_samples[n];
            float y = c.b0 * x + st.s1;
            st.s1 = c.b1 * x - c.a1 * y + st.s2;
            st.s2 = c.b2 * x - c.a2 * y;
            out_samples[n] = y;
        }

        ch_states[s] = st;
    }
}
