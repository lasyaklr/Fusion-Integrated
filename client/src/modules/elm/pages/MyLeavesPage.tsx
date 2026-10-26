import { useEffect, useState } from "react";
import {
  Badge, Button, Card, Container, Grid, Group, Stack, Table, Text, Title, Modal, Textarea
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function MyLeavesPage() {
  const [data, setData] = useState<{ balances: any[]; applications: any[] }>({ balances: [], applications: [] });
  const [loading, setLoading] = useState(true);
  const [cancelModal, setCancelModal] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [extensionApp, setExtensionApp] = useState<any | null>(null);
  const [extensionForm, setExtensionForm] = useState({ start_date: "", end_date: "", reason: "" });
  const [resumptionApp, setResumptionApp] = useState<any | null>(null);
  const [resumptionForm, setResumptionForm] = useState({ actual_date: "", remarks: "" });

  const fetchData = async () => {
    try {
      const res = await fetch("/api/v1/elm/my-leaves");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleWithdraw = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/elm/applications/${id}/withdraw`, { method: "POST" });
      if (res.ok) {
        notifications.show({ title: "Success", message: "Application withdrawn immediately." });
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCancelRequest = async () => {
    if (!cancelModal) return;
    try {
      const res = await fetch(`/api/v1/elm/applications/${cancelModal}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ remarks: cancelReason }),
      });
      if (res.ok) {
        notifications.show({ title: "Success", message: "Cancellation requested." });
        setCancelModal(null);
        setCancelReason("");
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleExtensionRequest = async () => {
    if (!extensionApp) return;
    try {
      const res = await fetch(`/api/v1/elm/applications/${extensionApp.id}/extend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          leave_category: extensionApp.leave_category,
          ...extensionForm,
        }),
      });
      if (!res.ok) throw new Error(`Could not request an extension (${res.status}).`);
      notifications.show({ title: "Success", message: "Leave extension requested." });
      setExtensionApp(null);
      setExtensionForm({ start_date: "", end_date: "", reason: "" });
      fetchData();
    } catch (e) {
      notifications.show({
        title: "Error",
        message: e instanceof Error ? e.message : "Could not request an extension.",
        color: "red",
      });
    }
  };

  const handleResumptionSubmit = async () => {
    if (!resumptionApp) return;
    try {
      const res = await fetch(`/api/v1/elm/applications/${resumptionApp.id}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resumptionForm),
      });
      if (!res.ok) throw new Error(`Could not submit the resumption report (${res.status}).`);
      notifications.show({ title: "Success", message: "Resumption report submitted." });
      setResumptionApp(null);
      setResumptionForm({ actual_date: "", remarks: "" });
      fetchData();
    } catch (e) {
      notifications.show({
        title: "Error",
        message: e instanceof Error ? e.message : "Could not submit the resumption report.",
        color: "red",
      });
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="View your leave balances and track leave application status"
      />

      <Stack gap="lg">
        <Title order={3}>Leave Balances</Title>
        <Grid>
          {data.balances.map((b) => (
            <Grid.Col key={b.id} span={{ base: 12, sm: 4, md: 2 }}>
              <Card shadow="sm" padding="md" withBorder>
                <Text size="xs" c="dimmed" fw={700}>{b.leave_category}</Text>
                <Title order={2}>{b.available_days}</Title>
                <Text size="xs" c="dimmed">Allocated: {b.allocated_days} | Availed: {b.availed_days}</Text>
              </Card>
            </Grid.Col>
          ))}
        </Grid>

        <Title order={3} mt="md">Leave Applications</Title>
        <Card shadow="sm" padding="md" withBorder>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Station Leave</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.applications.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td fw={600}>{app.leave_category}</Table.Td>
                  <Table.Td>{app.start_date} to {app.end_date}</Table.Td>
                  <Table.Td>{app.calculated_days}</Table.Td>
                  <Table.Td>
                    <Badge color={app.status === "approved" ? "green" : app.status === "rejected" ? "red" : "blue"}>
                      {app.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{app.is_station_leave ? "Yes (" + app.station_destination + ")" : "No"}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {["pending_substitute", "pending_unit_head", "pending_higher_sanction"].includes(app.status) && (
                        <Button size="xs" color="red" variant="subtle" onClick={() => handleWithdraw(app.id)}>
                          Withdraw
                        </Button>
                      )}
                      {app.status === "approved" && (
                        <>
                          <Button size="xs" color="orange" variant="subtle" onClick={() => setCancelModal(app.id)}>
                            Cancel
                          </Button>
                          {["EL", "COL", "VL"].includes(app.leave_category) && (
                            <>
                              <Button size="xs" variant="subtle" onClick={() => {
                                setExtensionApp(app);
                                setExtensionForm({ start_date: "", end_date: "", reason: "" });
                              }}>
                                Extend
                              </Button>
                              <Button size="xs" variant="subtle" onClick={() => {
                                setResumptionApp(app);
                                setResumptionForm({ actual_date: "", remarks: "" });
                              }}>
                                Report return
                              </Button>
                            </>
                          )}
                        </>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {data.applications.length === 0 && !loading && (
                <Table.Tr>
                  <Table.Td colSpan={6}>
                    <Text ta="center" c="dimmed" py="md">No leave applications recorded.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>

      <Modal opened={cancelModal !== null} onClose={() => setCancelModal(null)} title="Request Leave Cancellation">
        <Stack>
          <Text size="sm">Pre-start cancellation requests will be routed to the sanctioning hierarchy.</Text>
          <Textarea
            label="Reason for Cancellation"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModal(null)}>Back</Button>
            <Button color="orange" onClick={handleCancelRequest}>Submit Cancellation Request</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={extensionApp !== null} onClose={() => setExtensionApp(null)} title="Request Leave Extension">
        <Stack>
          <Text size="sm">Category: {extensionApp?.leave_category}</Text>
          <TextInput
            label="Extension Start Date"
            type="date"
            value={extensionForm.start_date}
            onChange={(e) => setExtensionForm({ ...extensionForm, start_date: e.target.value })}
            required
          />
          <TextInput
            label="Extension End Date"
            type="date"
            value={extensionForm.end_date}
            onChange={(e) => setExtensionForm({ ...extensionForm, end_date: e.target.value })}
            required
          />
          <Textarea
            label="Reason"
            value={extensionForm.reason}
            onChange={(e) => setExtensionForm({ ...extensionForm, reason: e.currentTarget.value })}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setExtensionApp(null)}>Back</Button>
            <Button onClick={handleExtensionRequest}>Submit Extension</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={resumptionApp !== null} onClose={() => setResumptionApp(null)} title="Report Return to Duty">
        <Stack>
          <TextInput
            label="Actual Return Date"
            type="date"
            value={resumptionForm.actual_date}
            onChange={(e) => setResumptionForm({ ...resumptionForm, actual_date: e.target.value })}
            required
          />
          <Textarea
            label="Remarks"
            value={resumptionForm.remarks}
            onChange={(e) => setResumptionForm({ ...resumptionForm, remarks: e.currentTarget.value })}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumptionApp(null)}>Back</Button>
            <Button onClick={handleResumptionSubmit}>Submit Report</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
