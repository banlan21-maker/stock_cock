import { redirect } from "next/navigation";

export default function StockAnalysisRedirectPage({
  params,
}: {
  params: { code: string };
}) {
  redirect(`/stock/${params.code}?tab=analysis`);
}
