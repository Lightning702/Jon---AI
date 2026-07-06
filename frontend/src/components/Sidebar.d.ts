import type { ConversationSummary } from "../lib/api";
interface Props {
    conversations: ConversationSummary[];
    activeId: string | null;
    onSelect: (id: string) => void;
    onNew: () => void;
    onDelete: (id: string) => void;
}
export default function Sidebar({ conversations, activeId, onSelect, onNew, onDelete, }: Props): import("react").JSX.Element;
export {};
