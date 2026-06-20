import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";

export function UserMenu() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-muted-foreground">{user.email}</span>
      <Button variant="outline" size="sm" onClick={logout}>
        Log out
      </Button>
    </div>
  );
}
