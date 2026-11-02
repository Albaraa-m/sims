import FactsEditor from "@/components/FactsEditor";
import InferredField from "@/components/InferredField";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { factsAsText, type TestFields } from "@/testFields";

type TestFieldsEditorProps = {
  fields: TestFields;
  onChange: (fields: TestFields) => void;
  // What the AI suggested, to label each field; null when it suggested nothing.
  aiFields: TestFields | null;
  aiLabel?: string;
};

export default function TestFieldsEditor({
  fields,
  onChange,
  aiFields,
  aiLabel,
}: TestFieldsEditorProps) {
  function updateField<K extends keyof TestFields>(
    field: K,
    value: TestFields[K],
  ) {
    onChange({ ...fields, [field]: value });
  }

  function inferenceOf(field: Exclude<keyof TestFields, "facts">) {
    // Older tests don't store the AI's name, so there's nothing to compare it with.
    const aiVersion = aiFields && aiFields[field] ? aiFields[field] : null;
    return {
      aiVersion,
      isEdited: aiVersion !== null && fields[field] !== aiVersion,
    };
  }

  return (
    <>
      <InferredField
        aiLabel={aiLabel}
        id="name"
        label="Name"
        {...inferenceOf("name")}
      >
        <Input
          id="name"
          value={fields.name}
          onChange={(event) => updateField("name", event.target.value)}
        />
      </InferredField>
      <FieldGroup
        title="Caller scenario"
        description="What the simulated caller wants, knows and does."
      >
        <InferredField
          aiLabel={aiLabel}
          id="goal"
          label="Goal"
          {...inferenceOf("goal")}
        >
          <Textarea
            id="goal"
            rows={2}
            value={fields.goal}
            onChange={(event) => updateField("goal", event.target.value)}
          />
        </InferredField>
        <InferredField
          aiLabel={aiLabel}
          label="Facts"
          aiVersion={aiFields && factsAsText(aiFields.facts)}
          isEdited={
            aiFields !== null &&
            JSON.stringify(fields.facts) !== JSON.stringify(aiFields.facts)
          }
        >
          <FactsEditor
            rows={fields.facts}
            onChange={(rows) => updateField("facts", rows)}
          />
        </InferredField>
        <InferredField
          aiLabel={aiLabel}
          id="behavior"
          label="Behavior"
          {...inferenceOf("behavior")}
        >
          <Textarea
            id="behavior"
            rows={3}
            value={fields.behavior}
            onChange={(event) => updateField("behavior", event.target.value)}
          />
        </InferredField>
      </FieldGroup>
      <FieldGroup
        title="Evaluation criteria"
        description="What the judge checks the agent against. The caller never sees these."
      >
        <InferredField
          aiLabel={aiLabel}
          id="policy-under-test"
          label="Policy under test"
          {...inferenceOf("policy_under_test")}
        >
          <Textarea
            id="policy-under-test"
            rows={2}
            value={fields.policy_under_test}
            onChange={(event) =>
              updateField("policy_under_test", event.target.value)
            }
          />
        </InferredField>
        <InferredField
          aiLabel={aiLabel}
          id="expected-outcome"
          label="Expected outcome"
          {...inferenceOf("expected_outcome")}
        >
          <Textarea
            id="expected-outcome"
            rows={2}
            value={fields.expected_outcome}
            onChange={(event) =>
              updateField("expected_outcome", event.target.value)
            }
          />
        </InferredField>
      </FieldGroup>
    </>
  );
}

function FieldGroup({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="space-y-4 border-t pt-4">
      <legend className="pr-2">
        <span className="text-sm font-semibold">{title}</span>
        <span className="ml-2 text-xs text-muted-foreground">
          {description}
        </span>
      </legend>
      {children}
    </fieldset>
  );
}
