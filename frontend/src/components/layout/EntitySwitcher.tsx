import { useNavigate, useParams } from "react-router-dom";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/auth/AuthContext";
import { setLastSelectedEntityId } from "@/lib/entityStorage";

export function EntitySwitcher() {
  const { user } = useAuth();
  const { entityId } = useParams<{ entityId: string }>();
  const navigate = useNavigate();

  if (!user || user.memberships.length === 0) {
    return null;
  }
  const memberships = user.memberships;

  function handleChange(newEntityId: string | null) {
    if (!newEntityId) return;
    setLastSelectedEntityId(newEntityId);
    navigate(`/entities/${newEntityId}/journal-entries`);
  }

  function labelFor(value: string | null) {
    const membership = memberships.find((m) => m.entity_id === value);
    return membership ? `${membership.entity_name} (${membership.role})` : null;
  }

  return (
    <Select value={entityId} onValueChange={handleChange}>
      <SelectTrigger className="w-[220px]">
        {/* Select.Value needs an explicit value->label mapping -- without
            it, the closed trigger shows the raw value (a UUID here), not
            the item's rendered children. */}
        <SelectValue placeholder="Select an entity">{labelFor}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {memberships.map((membership) => (
          <SelectItem
            key={membership.entity_id}
            value={membership.entity_id}
            label={`${membership.entity_name} (${membership.role})`}
          >
            {membership.entity_name} ({membership.role})
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
