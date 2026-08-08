"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import { api } from "@/lib/api";
import { Modal } from "@/components/dashboard/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { FILING_TYPE_LABELS, type FilingType, type StaffMember } from "@/lib/types";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function useStaffForAssignment(firmId: string | undefined) {
  return useQuery<StaffMember[]>({
    queryKey: ["users", firmId],
    queryFn: async () => (await api.get("/users", { params: { firm_id: firmId } })).data,
    enabled: !!firmId,
  });
}

const FILING_TYPES = Object.keys(FILING_TYPE_LABELS) as FilingType[];

export function NewFilingModal({
  open,
  onClose,
  clientId,
  firmId,
}: {
  open: boolean;
  onClose: () => void;
  clientId: string;
  firmId: string | undefined;
}) {
  const queryClient = useQueryClient();
  const { data: staff } = useStaffForAssignment(firmId);

  const [filingType, setFilingType] = useState<FilingType>("income_tax_return");
  const [periodLabel, setPeriodLabel] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [accountantId, setAccountantId] = useState("");

  const createFiling = useMutation({
    mutationFn: async () =>
      (
        await api.post("/filings", {
          client_id: clientId,
          filing_type: filingType,
          period_label: periodLabel || null,
          due_date: dueDate || null,
          assigned_accountant_id: accountantId || null,
        })
      ).data,
    onSuccess: () => {
      toast.success("Filing created");
      queryClient.invalidateQueries({ queryKey: ["filings"] });
      // Assigning an accountant here may backfill the client's default
      // accountant (see backend filings.py) — refetch so the "Accountant
      // assigned / Unassigned" badge on the client page reflects it.
      queryClient.invalidateQueries({ queryKey: ["clients", clientId] });
      setPeriodLabel("");
      setDueDate("");
      setAccountantId("");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err, "Couldn't create that filing.")),
  });

  return (
    <Modal open={open} onClose={onClose} title="New filing">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          createFiling.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <Label htmlFor="filing-type">Filing type</Label>
          <Select
            id="filing-type"
            value={filingType}
            onChange={(e) => setFilingType(e.target.value as FilingType)}
          >
            {FILING_TYPES.map((type) => (
              <option key={type} value={type}>
                {FILING_TYPE_LABELS[type]}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="period-label">Period</Label>
          <Input
            id="period-label"
            value={periodLabel}
            onChange={(e) => setPeriodLabel(e.target.value)}
            placeholder="FY 2025-26"
          />
        </div>
        <div>
          <Label htmlFor="due-date">Due date</Label>
          <Input
            id="due-date"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="filing-accountant">Assigned accountant (optional)</Label>
          <Select
            id="filing-accountant"
            value={accountantId}
            onChange={(e) => setAccountantId(e.target.value)}
          >
            <option value="">Unassigned</option>
            {(staff ?? [])
              .filter((s) => s.role !== "client")
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name} ({s.role.replace("_", " ")})
                </option>
              ))}
          </Select>
        </div>
        <Button type="submit" disabled={createFiling.isPending} className="w-full">
          {createFiling.isPending ? "Creating…" : "Create filing"}
        </Button>
      </form>
    </Modal>
  );
}
