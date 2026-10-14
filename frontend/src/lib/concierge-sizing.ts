export function conciergeWidthBounds(viewportWidth:number){
  const max=Math.max(280,Math.min(760,viewportWidth-16,viewportWidth<=1100?viewportWidth-32:viewportWidth*.48));
  return {min:Math.min(320,max),max};
}

export function clampConciergeWidth(width:number,viewportWidth:number){
  const {min,max}=conciergeWidthBounds(viewportWidth);
  return Math.round(Math.max(min,Math.min(max,width)));
}
