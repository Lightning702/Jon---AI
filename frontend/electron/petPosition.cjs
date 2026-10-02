function clampPosition(point, size, area) {
  return {
    x: Math.round(Math.max(area.x, Math.min(point.x, area.x + Math.max(0, area.width - size.width)))),
    y: Math.round(Math.max(area.y, Math.min(point.y, area.y + Math.max(0, area.height - size.height))))
  };
}

function dragPosition(cursor, offset) {
  return { x: Math.round(cursor.x - offset.x), y: Math.round(cursor.y - offset.y) };
}

module.exports = { clampPosition, dragPosition };
