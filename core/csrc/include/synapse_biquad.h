#ifndef SYNAPSE_BIQUAD_H
#define SYNAPSE_BIQUAD_H

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float b0;
    float b1;
    float b2;
    float a1;
    float a2;
} synapse_biquad_coeffs_t;

typedef struct {
    float s1;
    float s2;
} synapse_biquad_state_t;

typedef struct {
    uint32_t num_channels;
    uint32_t num_sections;
    synapse_biquad_coeffs_t *coeffs;
    synapse_biquad_state_t  *states;
} synapse_biquad_cascade_t;

int synapse_biquad_cascade_init(synapse_biquad_cascade_t *cascade,
                                uint32_t num_channels,
                                uint32_t num_sections,
                                const synapse_biquad_coeffs_t *coeffs);

void synapse_biquad_cascade_free(synapse_biquad_cascade_t *cascade);
void synapse_biquad_cascade_reset(synapse_biquad_cascade_t *cascade);
bool synapse_biquad_verify_stability(const synapse_biquad_coeffs_t *coeffs);

void synapse_biquad_process_sample(synapse_biquad_cascade_t *cascade,
                                   const float *in_frame,
                                   float *out_frame);

void synapse_biquad_process_block(synapse_biquad_cascade_t *cascade,
                                  uint32_t channel_idx,
                                  const float *in_samples,
                                  float *out_samples,
                                  size_t num_samples);

#ifdef __cplusplus
}
#endif

#endif /* SYNAPSE_BIQUAD_H */
