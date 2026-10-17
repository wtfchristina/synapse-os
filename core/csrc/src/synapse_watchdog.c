#include "synapse_watchdog.h"
#include <math.h>
#include <string.h>

void synapse_watchdog_init(synapse_watchdog_t *wd,
                           uint32_t num_channels,
                           const synapse_watchdog_config_t *config) {
    if (!wd || !config) return;
    wd->num_channels = num_channels;
    wd->config = *config;
    wd->clamp_counter = 0;
    wd->is_tripped = false;
}

bool synapse_watchdog_check_frame(synapse_watchdog_t *wd,
                                  const float *in_frame,
                                  float *out_frame) {
    if (!wd || !in_frame || !out_frame) return false;

    float trip_limit = wd->config.emg_trip_uv;
    bool trip_detected = false;

    for (uint32_t ch = 0; ch < wd->num_channels; ++ch) {
        if (fabsf(in_frame[ch]) >= trip_limit) {
            trip_detected = true;
            break;
        }
    }

    if (trip_detected) {
        wd->is_tripped = true;
        wd->clamp_counter = wd->config.holdoff_samples;
    } else if (wd->clamp_counter > 0) {
        wd->clamp_counter--;
        if (wd->clamp_counter == 0) {
            wd->is_tripped = false;
        }
    }

    if (wd->is_tripped) {
        memset(out_frame, 0, wd->num_channels * sizeof(float));
        return true;
    }

    if (in_frame != out_frame) {
        memcpy(out_frame, in_frame, wd->num_channels * sizeof(float));
    }
    return false;
}

void synapse_watchdog_reset(synapse_watchdog_t *wd) {
    if (wd) {
        wd->clamp_counter = 0;
        wd->is_tripped = false;
    }
}
