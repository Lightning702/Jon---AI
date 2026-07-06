export interface ToolStep {
    name: string;
    done: boolean;
    ok?: boolean;
}
export interface ChatEntry {
    id: string;
    role: "user" | "assistant";
    content: string;
    reasoning?: string;
    streaming?: boolean;
    tools?: ToolStep[];
}
export default function MessageBubble({ entry }: {
    entry: ChatEntry;
}): import("react").JSX.Element;
