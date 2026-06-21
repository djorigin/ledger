import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const CURRENCIES = ["AUD", "CNY", "USD"];

interface CurrencySelectProps {
  value: string;
  onChange: (value: string) => void;
}

export function CurrencySelect({ value, onChange }: CurrencySelectProps) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v ?? "AUD")}>
      <SelectTrigger>
        <SelectValue placeholder="Currency" />
      </SelectTrigger>
      <SelectContent>
        {CURRENCIES.map((currency) => (
          <SelectItem key={currency} value={currency} label={currency}>
            {currency}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
