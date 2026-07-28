/** Maps Flask's Proposal.to_dict() shape into what genesis_agent's Jinja
 * proposal template (templates/proposal/default.html) expects. */
export function toProposalTemplateData(proposal: any) {
  const company = proposal?.client?.company;
  return {
    number: `P-${proposal?.proposal_id ?? "0000"}`,
    date: proposal?.created_at
      ? new Date(proposal.created_at).toLocaleDateString()
      : undefined,
    title: company ? `${company} — Proposal` : "Proposal",
    status: proposal?.status,
    objectives: (proposal?.requirements_checklist ?? [])
      .map((r: any) => r?.text)
      .filter(Boolean),
    approach: proposal?.scope_of_work,
    deliverables: proposal?.deliverables ?? [],
    timeline: proposal?.timeline,
    client_name: proposal?.client?.name,
    client_company: company,
  };
}

/** Maps Flask's Quote.to_dict() shape (with its nested `proposal.client`)
 * into what genesis_agent's Jinja quote template
 * (templates/quote/default.html) expects. */
export function toQuoteTemplateData(quote: any) {
  const company = quote?.proposal?.client?.company;
  return {
    number: `Q-${quote?.quote_id ?? "0000"}`,
    date: quote?.created_at
      ? new Date(quote.created_at).toLocaleDateString()
      : undefined,
    title: company ? `${company} — Quotation` : "Quotation",
    status: quote?.status,
    currency: quote?.currency,
    line_items: (quote?.line_items ?? []).map((item: any) => ({
      item: item?.item,
      qty: item?.qty,
      unit_price: item?.unit_price,
      amount: item?.amount,
    })),
    tax_rate: quote?.tax_rate,
    client_name: quote?.proposal?.client?.name,
    client_company: company,
  };
}
