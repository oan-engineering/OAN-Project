# Crop Sown Registry — Roles & Permissions Plan

_Staff Portal access design: separating the person who **creates** data from the
person who **approves** it (separation of duties)._

---

## 1. Goal

We want two kinds of user:

1. **Creator** — creates records through the **Intake Form**, and raises
   corrections through the **"Edit Details" → Change Request** flow.
2. **Approver** — **approves** the intake-form submissions and the change
   requests that the Creator raises.

Right now **`admin`** is used for development, so it needs **everything**
(including schema / configuration access). Later, `admin` will be narrowed down
to a pure Creator, and a separate user will be the Approver.

---

## 2. The 3 users today (current state)

| User | Current Staff-Portal roles | Notes |
|---|---|---|
| **admin** | All 11 roles + `AWE_ADMIN` | Effectively a superuser |
| **alex.carter** | Technical Administrator, Operations Administrator | Same as nina.patel |
| **nina.patel** | Technical Administrator, Operations Administrator | Same as alex.carter |

> `alex.carter` and `nina.patel` currently have **identical** roles. They are
> set up as **AWE approvers** (AWE approvers are seeded with the
> "Operations Administrator" / "Technical Administrator" roles).

---

## 3. Role → capability reference

Only the capabilities relevant to this plan are shown. (Every role also grants
matching `view` permissions.)

| What the user can do | Permission behind it | Role that grants it |
|---|---|---|
| Create / edit a record via **Intake Form** | `intakeSubmission:edit` | **Intake Officer** |
| Raise a **Change Request** ("Edit Details") | `changeRequest:create` | **Data Editor** |
| **Approve** an intake-form submission | `intakeSubmission:approve` | **Intake Validator** |
| **Approve** a change request | `changeRequest:approve` | ⚠️ **only Technical Administrator** |
| Edit **schema / configuration** (sections, tabs, register defs, config) | `registerSection:edit`, `registerDefinition:edit`, `registryConfiguration:edit` | **Schema Designer** |
| Edit **data models** | `dataModel:edit` | **Integration Specialist** |
| **Everything** (all 72 permissions) | — | **Technical Administrator** |

**Key gap to be aware of:** there is a dedicated role to *approve intake forms*
(**Intake Validator**), but there is **no dedicated role to *approve change
requests*** — `changeRequest:approve` exists **only** inside
**Technical Administrator**.

---

## 4. The plan

### 4a. `admin` — now (development)

Assign **just one role: `Technical Administrator`**.

- It already includes **all 72 permissions**: create intake records, raise
  change requests, approve both, and full **schema / config / data-model**
  editing.
- So the other 10 roles are redundant — `Technical Administrator` alone gives
  the full access you need while developing.
- (Keep `AWE_ADMIN` on the `awe-admin-portal` client if you use the AWE portal.)

### 4b. `admin` — later (locked down to a pure Creator)

Swap `Technical Administrator` → **`Intake Officer` + `Data Editor`**.

| Role | Gives admin |
|---|---|
| Intake Officer | Create records via the Intake Form |
| Data Editor | Raise Change Requests via "Edit Details" |

Result: `admin` can **create** but can no longer **approve** or touch schema —
exactly the Creator persona.

### 4c. The Approver user (e.g. `nina.patel`)

- **Intake-form approval** → assign **`Intake Validator`** ✅ (dedicated role).
- **Change-request approval** → because `changeRequest:approve` lives only in
  `Technical Administrator`, choose one of the options below.

---

## 5. Change-request approval — 3 options (a decision for you)

| Option | What to do | Trade-off |
|---|---|---|
| **A** | Give the approver **`Technical Administrator`** | Works, but that's full access — breaks separation of duties |
| **B** | Approve through the **AWE workflow**; keep the approver on **Operations Administrator / Technical Administrator** (the AWE-approver roles) | This is how `alex.carter` / `nina.patel` are already configured |
| **C — recommended** | **Add `changeRequest:approve` to a dedicated role** (e.g. add it to **Data Validator** so it becomes a real "CR Approver"), then assign the approver **`Intake Validator` + `Data Validator`** | True separation: the approver can approve but has **no** create/schema rights. Requires a one-line edit to the IAM catalog |

---

## 6. Recommended final assignment

| User | Role(s) | Persona |
|---|---|---|
| **admin** (now) | `Technical Administrator` | Full access for development |
| **admin** (later) | `Intake Officer` + `Data Editor` | Creator only |
| **nina.patel** (approver) | `Intake Validator` + `Data Validator`* | Approver only |
| **alex.carter** | (spare) — e.g. a 2nd-stage AWE approver, or a Creator for testing | — |

\* assuming **Option C** — after `changeRequest:approve` is added to
`Data Validator`. With Option A/B, the approver keeps
`Technical Administrator` / `Operations Administrator` instead.

---

## 7. How the changes get applied

- **Role assignments** live in **Keycloak** (realm `staff`, client
  `cropsown-registry-staff-portal`). Changing them in the Keycloak admin
  console (or via `kcadm`) takes effect on the user's **next login**.
- To make the setup **reproducible** (survive a fresh environment / re-init),
  the same assignments should also be added to
  **`local/keycloak/keycloak-init.sh`**.
- **Option C** additionally requires editing the role→permission mapping in
  **`local/iam/cropsown-registry-iam-catalog.json`** (add `changeRequest:approve`
  to the `Data Validator` role), which is loaded by the IAM/registry.

---

## 8. Open decisions (need your input)

1. **Approver CR-approval:** Option **A**, **B**, or **C**? (Recommended: **C**.)
2. **`admin`:** set it to just `Technical Administrator` now, or leave its
   current 11 roles as-is until later?
3. **`alex.carter`:** what should this third user be — a second approver, or a
   Creator for testing?
