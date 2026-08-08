import { useEffect, useRef } from "react";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";

/**
 * Ensures the currently-authenticated student has a `behavior_student` document
 * in Firestore. Runs once per user_id (per session) whenever a user is loaded —
 * i.e. after login, signup, or on page refresh.
 *
 * Uses ONLY the existing Emergent Auth session (no Firebase Authentication).
 * Renders nothing.
 */
export default function FirestoreStudentProvisioner() {
  const { user } = useAuth();
  const provisionedRef = useRef(null);

  useEffect(() => {
    if (!user?.user_id) return;
    if (provisionedRef.current === user.user_id) return;
    if (user.is_admin) {
      provisionedRef.current = user.user_id;
      return;
    }
    provisionedRef.current = user.user_id;
    api.post("/firestore/students/me/ensure").catch(() => {
      // Silent — non-blocking. Firestore endpoints will auto-provision lazily anyway.
    });
  }, [user?.user_id]);

  return null;
}
