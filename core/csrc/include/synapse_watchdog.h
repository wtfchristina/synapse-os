#ifndef SYNAPSE_WATCHDOG_H
#define SYNAPSE_WATCHDOG_H

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float eog_trip_uv;          /* Peak ocular amplitude threshold (e.g. 150 uV) */
    float emg_trip_uv;          /* Peak myogenic amplitude threshold (e.g. 200 uV) */
    uint32_t holdoff_samples;   /* Minimum samples to clamp output after trip */
} synapse_watchdog_config_t;

typedef struct {
    synapse_watchdog_config_t config;
    uint32_t num_channels;
    uint32_t clamp_counter;     /* Remaining samples in tripped state */
    bool is_tripped;
} synapse_watchdog_t;

void synapse_watchdog_init(synapse_watchdog_t *wd,
                           uint32_t num_channels,
                           const synapse_watchdog_config_t *config);

/**
 * Evaluates a 1-sample multi-channel frame.
 * If any channel exceeds limits, trips watchdog and clamps out_frame to 0.0.
 * Returns true if tripped, false if clear.
 */
bool synapse_watchdog_check_frame(synapse_watchdog_t *wd,
                                  const float *in_frame,
                                  float *out_frame);

void synapse_watchdog_reset(synapse_watchdog_t *wd);

#ifdef __cplusplus
}
#endif

#endif /* SYNAPSE_WATCHDOG_H */
