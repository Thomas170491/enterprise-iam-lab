# G12 role-source evidence contract

This is the target evidence format. Composite paths are scheduled for Day 5.

Each effective employee-portal role has:

- `role_id`: Keycloak role ID, used to match roles.
- `role_name`: display name.
- `assignment_source`: `direct`, `inherited`, or `both`.
- `grant_sources`: every verified route by which the user receives the role.

Each grant source records:

- `type`: `user` or `group`.
- `assigned_role_id`: the role directly mapped to that user or group.
- `composite_path`: ordered role IDs from `assigned_role_id` to
  `role_id`; `[]` if the assigned and effective roles are the same.
- For a user source, `user_id`.
- For a group source, `group_id` (the group granting the role) and
  `membership_group_id` (the group the user belongs to).

`assignment_source` is `direct` for user sources, `inherited` for group
sources, and `both` when both exist. Never infer a group source merely
because a role is absent from the user's direct mappings.