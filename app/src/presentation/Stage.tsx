import type { PropsWithChildren, RefObject } from 'react';
export function Stage({children,stageRef}:PropsWithChildren<{stageRef:RefObject<HTMLElement|null>}>){
  return <section className="stage" aria-label="Game screen" ref={stageRef}><div className="stage-content">{children}</div></section>;
}
