# MAC Randomization — Why Aura Is Immune

A detailed explanation of MAC randomization, why it breaks MAC-based attendance systems, and why Aura is architecturally immune to it.

---

## What Is MAC Randomization?

Every network interface card has a **Media Access Control (MAC) address** — a 48-bit identifier burned into the hardware. Historically, devices always transmitted their real (globally unique, manufacturer-assigned) MAC when associating with Wi-Fi networks.

Starting with:
- **iOS 14** (2020) — random MAC per SSID, rotated periodically
- **Android 10** (2019) — random MAC per SSID by default
- **Windows 10 (1903)** (2019) — random MAC per network

Modern mobile devices no longer transmit their real MAC address when connecting to Wi-Fi. They present a **locally administered, randomly generated MAC** that changes per SSID and may rotate on a regular schedule.

---

## How MAC Randomization Breaks MAC-Based Attendance Systems

Any system that tracks attendance using MAC addresses as device identifiers faces a fundamental problem:

1. The attendance system enrolls student A's device with MAC `AA:BB:CC:01:02:03`
2. Student A's iPhone rotates its randomized MAC for the campus SSID
3. The device now presents MAC `52:F3:A1:9C:D4:E7` when connecting
4. The attendance system has no record of this MAC → **student appears absent**
5. Or worse: the rotated MAC collides with another device's previous random MAC → **wrong student is marked present**

This is not a theoretical edge case. It is the default behavior on every smartphone manufactured since 2019.

---

## Why Aura Is Immune

Aura's primary session identifier is the **RADIUS `User-Name`** attribute — not the MAC address.

The RADIUS `User-Name` travels inside the **802.1X/EAP tunnel**. This is a Layer 7 construct — the application layer of the network stack. It contains the student's institutional login credential, verified cryptographically by the EAP authentication exchange before any accounting event fires.

The MAC address (Layer 2) and the `User-Name` (Layer 7) operate independently:

```
Layer 2 (Data Link):    [Randomized MAC] ← rotates per SSID, meaningless for identity
                              ↓
Layer 3-6:              Standard IP/TCP stack
                              ↓
Layer 7 (Application):  [802.1X EAP tunnel]
                           └── [User-Name: stu.rahul03@college.edu] ← verified credential
```

MAC randomization affects what address the device presents in the 802.11 management frame. It has zero effect on the EAP tunnel contents, because that tunnel is authenticated at Layer 7 with the student's actual institutional credential.

---

## The MAC Field in Aura

`Calling-Station-Id` (the RADIUS attribute for the client MAC) is still stored in Aura's `devices` table and in `attendance_sessions.ap_name` — but it is a **secondary fingerprint**, not the primary key.

Its current use:
- **Diagnostic** — for detecting MAC clone attempts (suspicious `User-Name`/MAC pairings)
- **Device correlation** — for multi-device detection in future roadmap features

The `mac_clone_attempt` scenario specifically demonstrates how Aura handles a case where a `User-Name` appears on an unexpected AP with a MAC that doesn't match registered device patterns — something a purely MAC-based system would be blind to entirely.

---

## Summary

| Property | MAC-based system | Aura |
|---|---|---|
| Immune to MAC randomization | ❌ Broken by design | ✅ By design |
| Requires device enrollment | ✅ Yes | ❌ No |
| Student identity source | MAC lookup table | RADIUS User-Name (cryptographic) |
| Affected by iOS 14+ | ✅ Yes | ❌ No |
| Can detect MAC spoofing | ❌ No | ✅ Yes (secondary check) |
