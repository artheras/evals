#ifndef PID_H
#define PID_H

typedef struct {
    double kp, ki, kd;
    double out_min, out_max;
    double integral;
    double prev_measurement;
    int has_prev;
} pid_ctrl_t;

void pid_init(pid_ctrl_t *pid, double kp, double ki, double kd, double out_min, double out_max);
double pid_update(pid_ctrl_t *pid, double setpoint, double measurement, double dt);

#endif
