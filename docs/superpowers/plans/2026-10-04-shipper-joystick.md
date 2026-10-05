# Courier joystick and reverse

User requested reverse and a circular drag control in the existing local preview. Keep the first-person street view and all server trip/traffic contracts.

Design: fixed circular joystick, up/down controls forward/reverse throttle and left/right steers; diagonals combine them. Release returns to centre and coasts to a stop. Retain separate gas/brake buttons. Keyboard W/up forward, S/down reverse, A/D steer, Space brake. Opposite throttle brakes through zero before reversing; reverse is limited to 4 m/s. Map/help, blur, cancellation and closing clear all held input. Signed speed must not bypass collisions, stop detection or traffic checkpoints.

- [x] Add and run failing pure control tests (dead zone, clamp, proportional throttle, reverse cap, direction changes, braking).
- [x] Implement controls helper, joystick pointer capture, signed movement and traffic/arrival guards in delivery_drive.js.
- [x] Update responsive CSS, visible control hints and English translations.
- [x] Run courier/traffic regression tests and browser drag/reverse/pause checks; review code and open local preview. No deploy.
