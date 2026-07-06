export interface ChatMessage {
    role: "system" | "user" | "assistant";
    content: string;
}
export interface ProviderStatus {
    provider: string;
    configured: boolean;
    env_var: string;
    models: string[];
}
export interface ConversationSummary {
    id: string;
    title: string;
    provider: string;
    model: string;
    created_at: string;
    updated_at: string;
}
export interface Health {
    status: string;
    app: string;
    version: string;
    default_provider: string;
    default_model: string;
    available_providers: string[];
}
export interface StreamEvent {
    type: "meta" | "content" | "reasoning" | "tool" | "error" | "done";
    delta?: string;
    message?: string;
    provider?: string;
    model?: string;
    conversation_id?: string;
    name?: string;
    status?: "running" | "done";
    ok?: boolean;
}
export interface StreamHandlers {
    onMeta?: (e: StreamEvent) => void;
    onContent?: (delta: string) => void;
    onReasoning?: (delta: string) => void;
    onTool?: (e: StreamEvent) => void;
    onError?: (message: string) => void;
    onDone?: (conversationId?: string) => void;
}
export declare function transcribeAudio(wav: Blob): Promise<string>;
export declare function getHealth(): Promise<Health>;
export declare function getProviders(): Promise<ProviderStatus[]>;
export declare function getConversations(): Promise<ConversationSummary[]>;
export declare function getConversation(id: string): Promise<any>;
export declare function deleteConversation(id: string): Promise<void>;
export declare function streamChat(body: {
    messages: ChatMessage[];
    provider?: string;
    model?: string;
    temperature?: number;
    conversation_id?: string | null;
    persist?: boolean;
}, handlers: StreamHandlers, signal?: AbortSignal): Promise<void>;
