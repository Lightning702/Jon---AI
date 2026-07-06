import type { ProviderStatus } from "../lib/api";
interface Props {
    providers: ProviderStatus[];
    provider: string;
    model: string;
    onChange: (provider: string, model: string) => void;
}
export default function ModelPicker({ providers, provider, model, onChange, }: Props): import("react").JSX.Element;
export {};
