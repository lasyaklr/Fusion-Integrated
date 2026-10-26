import { useEffect, useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Select, Stack, Table, Text, Textarea, Title
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ApprovalsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [actionItem, setActionItem] = useState<any | null>(null);
  const [actionType, setActionType] = useState<"recommend" | "sanction" | "cancellation" | "resumption">("recommend");
  const [decision, setDecision] = useState("recommended");
  const [remarks, setRemarks] = useState("");

  const fetchItems = async () => {
    try {
      const res = await fetch("/api/v1/elm/approvals/pending");
      if (!res.ok) throw new Error(`Could not load approvals (${res.status}).`);
      setItems(await res.json());
    } catch (e) {
      notifications.show({
        title: "Error",
        message: e instanceof Error ? e.message : "Could not load approvals.",
        color: "red",
      });
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleAction = async () => {
    if (!actionItem) return;
    const paths = {
      recommend: "recommend",
      sanction: "sanction",
      cancellation: "cancellation-decision",
      resumption: "resumption-review",
    };
    const url = `/api/v1/elm/applications/${actionItem.id}/${paths[actionType]}`;

    const body = actionType === "recommend"
      ? { recommendation: decision, remarks }
      : { decision, remarks };

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Could not record the decision (${res.status}).`);
      notifications.show({ title: "Success", message: "Action recorded." });
      setActionItem(null);
      setRemarks("");
      await fetchItems();
    } catch (e) {
      notifications.show({
        title: "Error",
        message: e instanceof Error ? e.message : "Could not record the decision.",
        color: "red",
      });
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Approvals"
        subtitle="Review applications, record recommendations, or give final sanction"
      />

      <Card shadow="sm" padding="md" withBorder>
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Applicant (ID)</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Substitute Consent</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>User #{item.user_id}</Table.Td>
                <Table.Td><Badge>{item.leave_category}</Badge></Table.Td>
                <Table.Td>{item.start_date} to {item.end_date}</Table.Td>
                <Table.Td>{item.calculated_days}</Table.Td>
                <Table.Td><Badge color="blue">{item.status}</Badge></Table.Td>
                <Table.Td>{item.substitute_status || "N/A"}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {item.status === "pending_unit_head" && (
                      <Button size="xs" onClick={() => {
                        setActionItem(item);
                        setActionType("recommend");
                        setDecision(item.leave_category === "CL" || item.leave_category === "RH" ? "approved" : "recommended");
                      }}>
                        Review / Decide
                      </Button>
                    )}
                    {item.status === "pending_higher_sanction" && (
                      <Button size="xs" color="teal" onClick={() => {
                        setActionItem(item);
                        setActionType("sanction");
                        setDecision("approved");
                      }}>
                        Sanction
                      </Button>
                    )}
                    {item.status === "cancellation_requested" && (
                      <Button size="xs" color="orange" onClick={() => {
                        setActionItem(item);
                        setActionType("cancellation");
                        setDecision("approved");
                      }}>
                        Review cancellation
                      </Button>
                    )}
                    {item.resumption_status === "pending" && (
                      <Button size="xs" color="grape" onClick={() => {
                        setActionItem(item);
                        setActionType("resumption");
                        setDecision("approved");
                      }}>
                        Review resumption
                      </Button>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {items.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text ta="center" c="dimmed" py="md">No pending approvals.</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={actionItem !== null} onClose={() => setActionItem(null)} title="Record Review Decision">
        <Stack>
          <Text size="sm">Applicant: User #{actionItem?.user_id} | Category: {actionItem?.leave_category}</Text>
          <Select
            label="Decision"
            value={decision}
            onChange={(val) => setDecision(val || "")}
            data={
              actionType === "recommend" && !["CL", "RH"].includes(actionItem?.leave_category)
                ? [
                    { value: "recommended", label: "Recommended" },
                    { value: "not_recommended", label: "Not Recommended" },
                  ]
                : [
                    { value: "approved", label: "Approve" },
                    { value: "rejected", label: "Reject" },
                  ]
            }
          />
          <Textarea
            label="Remarks"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActionItem(null)}>Cancel</Button>
            <Button color="blue" onClick={handleAction}>Submit Decision</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
