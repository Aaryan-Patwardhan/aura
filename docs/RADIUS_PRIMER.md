# RADIUS Primer

A concise explanation of what RADIUS is, how 802.1X authentication works, and why it is the right data source for passive attendance.

---

## What Is RADIUS?

**Remote Authentication Dial-In User Service (RADIUS)** is a networking protocol (RFC 2865/2866) that provides centralized Authentication, Authorization, and Accounting (AAA) for network access. Originally designed for dial-up modem pools, it is now the universal protocol behind enterprise Wi-Fi, VPN gateways, and wired 802.1X port authentication.

In a campus Wi-Fi deployment, RADIUS sits between the Wireless LAN Controller (WLC) and the institution's identity backend (Active Directory / LDAP):

```
Student Device ──── 802.11 ──▶ Access Point ──▶ Wireless LAN Controller
                                                         │
                                                    RADIUS ↕
                                                         │
                                               RADIUS Server (FreeRADIUS / Cisco ISE)
                                                         │
                                                    LDAP/AD ↕
                                                         │
                                             Institution Identity Store
```

---

## 802.1X Authentication Flow

When a student's device connects to the campus SSID:

1. **Association** — The device associates at Layer 2. The AP does not forward any traffic yet.
2. **EAP negotiation** — The WLC sends an EAP (Extensible Authentication Protocol) request. The device and the RADIUS server negotiate an EAP method (PEAP, EAP-TLS, etc.).
3. **Credential exchange** — The student's device presents its institutional username and password (or certificate) inside the encrypted EAP tunnel.
4. **RADIUS Access-Accept** — The RADIUS server validates the credential against AD. If valid, it returns Access-Accept. The WLC opens the port and the student gets network access.
5. **RADIUS Accounting-Start** — The WLC immediately sends an `Accounting-Start` packet to the RADIUS server containing the verified `User-Name`, the AP identifier (`Called-Station-Id`), and session metadata.

The `User-Name` in step 5 is the same credential the student proved in step 3. It is **not** supplied by the device alone — it is the outcome of a cryptographically verified authentication exchange.

---

## RADIUS Accounting Packets

Three packet types matter for Aura:

| Packet Type | Trigger | Key Attributes |
|---|---|---|
| `Accounting-Start` | Student connects + authenticates | `User-Name`, `Called-Station-Id`, `Calling-Station-Id` (MAC), `NAS-IP-Address` |
| `Accounting-Interim-Update` | Periodic WLC poll (every 60–300s) | All above + `Acct-Input-Octets`, `Acct-Output-Octets`, `Acct-Session-Time` |
| `Accounting-Stop` | Student disconnects or roams away | All interim fields at final values |

`Acct-Input-Octets` = bytes uploaded by the **client** (from AP's perspective, = bytes received by AP from client).  
`Acct-Output-Octets` = bytes downloaded by the **client** (from AP's perspective, = bytes sent by AP to client).

---

## Why `Called-Station-Id` Maps to a Room

`Called-Station-Id` is the AP identifier — typically formatted as `BSSID:AP-Name` by Cisco/Aruba WLCs. The AP is a fixed piece of physical infrastructure installed in a specific room. The `access_points` table in Aura maps AP names to `room_id` values, creating an indirect but reliable binding:

```
User authenticates → RADIUS User-Name (identity)
Device associates → AP identifier (physical location)
AP → room_id (room)
```

This is the chain that lets Aura determine which room a student is in without any GPS, Bluetooth, or active cooperation from the student.

---

## What Aura Does Not Need

- RADIUS server access — Aura only needs the **accounting logs** forwarded from the WLC
- Active directory integration — the User-Name is already resolved by the WLC
- Real-time packet sniffing — accounting logs are standard syslog/UDP output from any enterprise WLC
- Student app or agent — the student device has no awareness that attendance is being tracked
