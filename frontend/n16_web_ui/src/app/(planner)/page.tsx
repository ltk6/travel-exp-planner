import { TitleBlock } from "@/components/header/title-block";
import { ModeTabs } from "@/components/header/mode-tabs";
import { InputArea } from "@/components/input/input-area";
import { SubmitBar } from "@/components/input/submit-bar";
import { StatsBar } from "@/components/input/stats-bar";

export default function HomePage() {
  return (
    <>
      <TitleBlock />
      <div className="mt-2 space-y-5">
        <ModeTabs />
        <StatsBar />
        <InputArea />
        <SubmitBar />
      </div>
    </>
  );
}
